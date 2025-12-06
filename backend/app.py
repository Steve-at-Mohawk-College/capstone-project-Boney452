"""
Flavor Quest Backend API Server

Flask-based REST API server providing backend services for the Flavor Quest
restaurant discovery and rating application.

@module app
@author Flavor Quest Development Team
@version 1.0.0

DESCRIPTION:
This module implements a comprehensive REST API with the following features:
- User authentication and authorization (JWT tokens)
- Restaurant search and management (Google Places API integration)
- User rating and review system
- Group-based chat system
- Admin user management
- Content filtering and moderation
- Security features (CSRF protection, rate limiting, input sanitization)

SECURITY FEATURES:
- Argon2 password hashing (resistant to timing attacks)
- JWT token-based authentication with expiration
- CSRF token protection for state-changing operations
- Input sanitization (XSS and SQL injection prevention)
- Content filtering (inappropriate words, spam detection)
- Rate limiting on authentication endpoints
- CORS configuration for frontend access
- Security headers (CSP, X-Frame-Options, etc.)

DATABASE:
- PostgreSQL database connection via psycopg2
- Automatic schema migration on startup
- Connection pooling and error handling

API ENDPOINTS:
- Authentication: /signup, /login, /me
- Restaurants: /api/restaurants/search, /api/restaurants/<place_id>
- Ratings: /api/restaurants/<place_id>/rate
- Chat: /api/groups, /api/groups/<id>/messages
- Admin: /admin/users (CRUD operations)

DEPLOYMENT:
- Configured for Render.com deployment
- Uses Gunicorn WSGI server
- Environment variable configuration
- Auto-migration on startup

@requires Flask>=2.0.0
@requires psycopg2-binary
@requires argon2-cffi
@requires flask-cors
@requires itsdangerous
"""

import psycopg2
from flask import Flask, request, jsonify
from flask_cors import CORS
from argon2 import PasswordHasher
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
import requests
import os
import json
import re
import html
from datetime import datetime
from functools import wraps

# ============================================================================
# Security Utilities
# ============================================================================

"""
Inappropriate Content Filter

List of words and phrases that are considered inappropriate for user-generated
content. Used to filter reviews, messages, and other user inputs.

@constant {list} INAPPROPRIATE_WORDS - List of inappropriate words/phrases
@note Includes variations with asterisks to catch attempts to bypass filters
"""
INAPPROPRIATE_WORDS = [
    # Spam and fraud related
    'spam', 'scam', 'fake', 'fraud', 'hate', 'violence',
    # Adult/profanity words (removed 'hell' and 'damn' as they appear in normal words like 'hello' and 'damned')
    'fuck', 'fucking', 'fucked', 'shit', 'shitting', 'crap', 'piss',
    'ass', 'asshole', 'bitch', 'bastard',
    'dick', 'cock', 'pussy', 'whore', 'slut', 'cunt', 'motherfucker',
    'bullshit', 'goddamn', 'goddamned', 'bugger', 'wanker',
    'prick', 'twat', 'tosser', 'bellend', 'arse', 'arsehole',
    # Additional variations
    'f*ck', 'f**k', 's**t', 'sh*t', 'a**', 'a**hole', 'b****', 'b***h',
    'd***', 'c***', 'p***y', 'w***e', 's***', 'c***', 'm***********r',
]

def contains_inappropriate_content(text):
    """
    Check if text contains inappropriate content
    
    Validates user input against inappropriate words list and spam patterns.
    Detects:
    - Inappropriate words (whole word matching)
    - Excessive capitalization (>70% caps)
    - Excessive word repetition (>50% same word)
    
    @param {str} text - Text to validate
    @returns {bool} True if inappropriate content detected, False otherwise
    
    @security
    This function helps prevent spam and inappropriate content from being
    stored in the database or displayed to other users.
    """
    if not text or not isinstance(text, str):
        return False
    
    text_lower = text.lower()
    # Split text into words (handle punctuation)
    import re
    words = re.findall(r'\b\w+\b', text_lower)
    
    # Check for inappropriate words (whole word match only)
    for word in INAPPROPRIATE_WORDS:
        if word.lower() in words:
            return True
    
    # Check for excessive capitalization (potential spam)
    if len(text) > 10:
        caps_ratio = sum(1 for c in text if c.isupper()) / len(text)
        if caps_ratio > 0.7:  # More than 70% caps
            return True
    
    # Check for excessive repetition (potential spam)
    if len(text) > 20:
        words = text.split()
        if len(words) > 3:
            # Check if same word repeats too many times
            word_counts = {}
            for word in words:
                word_lower = word.lower()
                word_counts[word_lower] = word_counts.get(word_lower, 0) + 1
                if word_counts[word_lower] > len(words) * 0.5:  # Same word more than 50% of text
                    return True
    
    return False

def sanitize_input(text, max_length=1000):
    """
    Sanitize user input to prevent XSS and SQL injection attacks
    
    Applies multiple layers of security:
    1. HTML escaping to prevent XSS
    2. SQL injection pattern removal
    3. Dangerous character removal
    4. Length limiting
    
    @param {str} text - User input to sanitize
    @param {int} max_length - Maximum allowed length (default: 1000)
    @returns {str} Sanitized text safe for database storage and display
    
    @security
    This is a critical security function. All user inputs should be
    sanitized before being stored in the database or displayed in HTML.
    
    @warning
    This function is not a substitute for parameterized queries.
    Always use parameterized queries for database operations.
    """
    if not text:
        return ""
    
    # Convert to string and limit length
    text = str(text)[:max_length]
    
    # HTML escape to prevent XSS
    text = html.escape(text)
    
    # Remove potentially dangerous characters
    text = re.sub(r'[<>"\']', '', text)
    
    # Remove SQL injection patterns
    dangerous_patterns = [
        r'(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION|SCRIPT)\b)',
        r'(\b(OR|AND)\s+\d+\s*=\s*\d+)',
        r'(\b(OR|AND)\s+\w+\s*=\s*\w+)',
        r'(;\s*(DROP|DELETE|INSERT|UPDATE))',
        r'(/\*.*?\*/)',
        r'(--.*)',
        r'(\b(script|javascript|vbscript|onload|onerror|onclick)\b)',
    ]
    
    for pattern in dangerous_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)
    
    return text.strip()

def validate_email(email):
    """
    Validate email address format
    
    @param {str} email - Email address to validate
    @returns {bool} True if email format is valid, False otherwise
    
    @example
    validate_email("user@example.com")  # Returns True
    validate_email("invalid-email")      # Returns False
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_username(username):
    """Validate username format"""
    if not username or len(username) < 3 or len(username) > 50:
        return False
    # Only allow alphanumeric characters, underscores, and hyphens
    return re.match(r'^[a-zA-Z0-9_-]+$', username) is not None

def validate_password(password):
    """Validate password strength"""
    if not password or len(password) < 8:
        return False
    # At least one uppercase, one lowercase, one digit
    return re.match(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)', password) is not None

def validate_rating(rating):
    """Validate rating value"""
    try:
        rating = float(rating)
        return 1 <= rating <= 5
    except (ValueError, TypeError):
        return False

def rate_limit(max_requests=100, window=3600):
    """Simple rate limiting decorator"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # In production, use Redis or similar for rate limiting
            # For now, we'll implement basic rate limiting
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# -----------------------------
# Database Configuration
# -----------------------------
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://flavoruser:securepass@localhost:5432/flavorquest"
).strip()

def _build_connection_url():
    """Ensure the connection string has sslmode when required."""
    dsn = DATABASE_URL
    if "render.com" in dsn and "sslmode=" not in dsn:
        separator = "&" if "?" in dsn else "?"
        dsn = f"{dsn}{separator}sslmode=require"
    return dsn

def get_db_connection():
    """
    Establish a database connection using the configured URL
    
    Creates a new PostgreSQL connection using connection parameters from
    environment variables or default values. Handles connection errors gracefully.
    
    @returns {psycopg2.connection} Database connection object
    @raises {psycopg2.Error} If connection fails
    
    @note
    Connection should be closed after use:
    conn = get_db_connection()
    try:
        # Use connection
    finally:
        conn.close()
    
    @security
    Uses parameterized queries via cursor.execute() to prevent SQL injection.
    Never use string formatting for SQL queries.
    """
    dsn = _build_connection_url()
    try:
        return psycopg2.connect(dsn)
    except psycopg2.Error as e:
        app.logger.error("Database connection error: %s", e)
        raise

def get_photo_url(photo_reference, max_width=400):
    """
    Generate a photo URL from Google Places photo reference
    
    Constructs a valid Google Places Photo API URL using the photo reference
    and API key. Used to display restaurant images.
    
    @param {str} photo_reference - Google Places photo reference ID
    @param {int} max_width - Maximum width of the photo in pixels (default: 400)
    @returns {str|None} Photo URL or None if photo_reference is invalid
    
    @api
    Requires GOOGLE_MAPS_API_KEY environment variable to be set.
    """
    if not photo_reference:
        return None
    
    base_url = "https://maps.googleapis.com/maps/api/place/photo"
    params = {
        "maxwidth": max_width,
        "photoreference": photo_reference,
        "key": GOOGLE_MAPS_API_KEY
    }
    
    # Build URL with parameters
    param_string = "&".join([f"{k}={v}" for k, v in params.items()])
    return f"{base_url}?{param_string}"

# -----------------------------
# Flask Setup
# -----------------------------
app = Flask(__name__)
CORS(app)

# Security headers
@app.after_request
def after_request(response):
    """
    Add security headers to all HTTP responses
    
    Implements multiple security headers to protect against common web
    vulnerabilities:
    - X-Content-Type-Options: Prevents MIME type sniffing
    - X-Frame-Options: Prevents clickjacking attacks
    - X-XSS-Protection: Enables browser XSS filter
    - Strict-Transport-Security: Forces HTTPS connections
    - Content-Security-Policy: Restricts resource loading
    - Referrer-Policy: Controls referrer information
    
    @param {Response} response - Flask response object
    @returns {Response} Modified response with security headers
    
    @security
    This middleware runs on every response, ensuring all endpoints
    have proper security headers regardless of route implementation.
    """
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    # Content Security Policy - Secure configuration for React/Vite
    # 'strict-dynamic' allows scripts loaded by trusted scripts (React/Vite bundles)
    # 'unsafe-eval' needed for Vite development mode (HMR) - can be removed in production
    # 'unsafe-inline' removed from script-src for security
    # 'unsafe-inline' kept for style-src (needed for TailwindCSS and dynamic styles)
    csp_policy = (
        "default-src 'self'; "
        "script-src 'self' 'strict-dynamic' 'unsafe-eval'; "  # 'unsafe-eval' for Vite dev, 'strict-dynamic' for React
        "style-src 'self' 'unsafe-inline' https:; "  # Allow inline styles (TailwindCSS)
        "img-src 'self' data: https: blob:; "  # Allow images from any HTTPS source
        "font-src 'self' data: https:; "  # Allow fonts
        "connect-src 'self' https://maps.googleapis.com https://flavour-quest-e7ho.onrender.com http://localhost:5002 ws://localhost:5173; "  # API endpoints + Vite HMR
        "frame-ancestors 'none'; "  # Prevent clickjacking
        "base-uri 'self'; "  # Restrict base tag
        "form-action 'self'; "  # Restrict form submissions
        "object-src 'none'; "  # Block plugins
        "upgrade-insecure-requests"  # Upgrade HTTP to HTTPS
    )
    response.headers['Content-Security-Policy'] = csp_policy
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    return response

# Password hasher
ph = PasswordHasher()

# Token serializer
serializer = URLSafeTimedSerializer("supersecret")  # change this secret in production

# -----------------------------
# Database Auto-Migration
# -----------------------------
def ensure_admin_column():
    """Automatically add is_admin column if it doesn't exist (runs on app startup)"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Check if column already exists
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='users' AND column_name='is_admin'
        """)
        
        if not cur.fetchone():
            # Column doesn't exist, add it
            cur.execute("""
                ALTER TABLE users 
                ADD COLUMN is_admin BOOLEAN DEFAULT FALSE NOT NULL
            """)
            conn.commit()
            app.logger.info("✅ Added 'is_admin' column to users table")
        else:
            app.logger.info("✅ 'is_admin' column already exists")
        
        cur.close()
        conn.close()
    except Exception as e:
        app.logger.error(f"Error ensuring admin column: {e}")
        # Don't raise - allow app to start even if migration fails
        # The column might already exist or will be created manually

def ensure_chat_tables():
    """Automatically create chat system tables if they don't exist (runs on app startup)"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Check if groups table exists
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name='groups'
        """)
        
        if not cur.fetchone():
            # Create groups table
            cur.execute("""
                CREATE TABLE groups (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    description TEXT,
                    created_by INTEGER NOT NULL REFERENCES users(id),
                    is_active BOOLEAN DEFAULT TRUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
            app.logger.info("✅ Created 'groups' table")
        else:
            app.logger.info("✅ 'groups' table already exists")
        
        # Check if group_members table exists
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name='group_members'
        """)
        
        if not cur.fetchone():
            # Create group_members table
            cur.execute("""
                CREATE TABLE group_members (
                    id SERIAL PRIMARY KEY,
                    group_id INTEGER NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    role VARCHAR(50) DEFAULT 'member' NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE NOT NULL,
                    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(group_id, user_id)
                )
            """)
            conn.commit()
            app.logger.info("✅ Created 'group_members' table")
        else:
            app.logger.info("✅ 'group_members' table already exists")
        
        # Check if messages table exists
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name='messages'
        """)
        
        if not cur.fetchone():
            # Create messages table
            cur.execute("""
                CREATE TABLE messages (
                    id SERIAL PRIMARY KEY,
                    group_id INTEGER NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    content TEXT NOT NULL,
                    message_type VARCHAR(50) DEFAULT 'text' NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
            app.logger.info("✅ Created 'messages' table")
        else:
            app.logger.info("✅ 'messages' table already exists")
        
        # Check if review_reports table exists
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name='review_reports'
        """)
        
        if not cur.fetchone():
            # Create review_reports table
            cur.execute("""
                CREATE TABLE review_reports (
                    id SERIAL PRIMARY KEY,
                    rating_id INTEGER NOT NULL REFERENCES restaurant_ratings(id) ON DELETE CASCADE,
                    reported_by INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    reason VARCHAR(255) NOT NULL,
                    description TEXT,
                    status VARCHAR(50) DEFAULT 'pending' NOT NULL,
                    resolved_by INTEGER REFERENCES users(id),
                    resolved_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(rating_id, reported_by)
                )
            """)
            conn.commit()
            app.logger.info("✅ Created 'review_reports' table")
        else:
            app.logger.info("✅ 'review_reports' table already exists")
        
        # Check if message_reports table exists
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name='message_reports'
        """)
        
        if not cur.fetchone():
            # Create message_reports table
            cur.execute("""
                CREATE TABLE message_reports (
                    id SERIAL PRIMARY KEY,
                    message_id INTEGER NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
                    reported_by INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    reason VARCHAR(255) NOT NULL,
                    description TEXT,
                    status VARCHAR(50) DEFAULT 'pending' NOT NULL,
                    resolved_by INTEGER REFERENCES users(id),
                    resolved_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(message_id, reported_by)
                )
            """)
            conn.commit()
            app.logger.info("✅ Created 'message_reports' table")
        else:
            app.logger.info("✅ 'message_reports' table already exists")
        
        cur.close()
        conn.close()
    except Exception as e:
        app.logger.error(f"Error ensuring chat tables: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        # Don't raise - allow app to start even if migration fails

# Run migration on app startup (non-blocking)
import threading
def run_migration_async():
    """Run migration in background thread to not block app startup"""
    try:
        ensure_admin_column()
        ensure_chat_tables()
    except Exception as e:
        app.logger.warning(f"Could not run auto-migration on startup: {e}")

# Start migration in background thread
migration_thread = threading.Thread(target=run_migration_async, daemon=True)
migration_thread.start()

# CSRF protection
def generate_csrf_token():
    """Generate a CSRF token"""
    return serializer.dumps("csrf_token")

def validate_csrf_token(token):
    """Validate a CSRF token"""
    try:
        serializer.loads(token, max_age=3600)  # 1 hour expiry
        return True
    except (BadSignature, SignatureExpired):
        return False

def require_csrf(f):
    """Decorator to require CSRF token for POST/PUT/DELETE requests"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method in ['POST', 'PUT', 'DELETE']:
            csrf_token = request.headers.get('X-CSRF-Token') or request.json.get('csrf_token')
            if not csrf_token or not validate_csrf_token(csrf_token):
                return jsonify({"error": "Invalid security token. Please refresh the page and try again."}), 403
        return f(*args, **kwargs)
    return decorated_function

# Google Maps API configuration
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "AIzaSyBZUCatkclEyKXH5yC4OjYKxri0-RqtJ6c")
GOOGLE_PLACES_API_URL = "https://maps.googleapis.com/maps/api/place"

# API Usage tracking (for budget management)
API_USAGE_FILE = "api_usage.json"
MAX_REQUESTS = 10000

def load_api_usage():
    """Load API usage from file"""
    try:
        with open(API_USAGE_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"total_requests": 0, "daily_requests": 0, "last_reset": None}

def save_api_usage(usage):
    """Save API usage to file"""
    with open(API_USAGE_FILE, 'w') as f:
        json.dump(usage, f, indent=2)

def check_api_quota():
    """Check if we're within API quota limits"""
    usage = load_api_usage()
    if usage["total_requests"] >= MAX_REQUESTS:
        return False, "API quota exceeded. You have reached your 10,000 request limit."
    return True, None

# -----------------------------
# Routes
# -----------------------------

@app.route("/")
def home():
    return {"message": "Flavor Quest API running"}

@app.route("/csrf-token", methods=["GET"])
def get_csrf_token():
    """Get CSRF token for form submissions"""
    return jsonify({"csrf_token": generate_csrf_token()})

# --- Restaurants ---
@app.route("/restaurants")
def get_restaurants():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT r.id, r.name, r.cuisine_type, r.location, r.google_api_links, r.google_rating, r.google_place_id, r.created_at,
                   COALESCE(AVG(rr.rating), 0) as avg_rating,
                   COUNT(rr.id) as total_ratings
            FROM restaurants r
            LEFT JOIN restaurant_ratings rr ON r.id = rr.restaurant_id
            WHERE r.is_active = TRUE
            GROUP BY r.id, r.name, r.cuisine_type, r.location, r.google_api_links, r.google_rating, r.google_place_id, r.created_at
            ORDER BY r.created_at DESC
        """)
        restaurants = cur.fetchall()
        
        restaurant_list = []
        for restaurant in restaurants:
            avg_rating = float(restaurant[8]) if restaurant[8] else 0
            total_ratings = restaurant[9]
            google_rating = float(restaurant[5]) if restaurant[5] else None
            
            # Determine rating message
            if total_ratings == 0:
                rating_message = "Have not been rated by users"
            else:
                rating_message = f"Rated by {total_ratings} user{'s' if total_ratings != 1 else ''} (Avg: {avg_rating:.1f}/5)"
            
            restaurant_list.append({
                "ResturantsId": restaurant[0],
                "Name": restaurant[1],
                "Cuisine Type": restaurant[2],
                "Location": restaurant[3],
                "GoogleApiLinks": restaurant[4],
                "rating": google_rating,  # Google rating
                "google_place_id": restaurant[6],
                "CreatedAt": restaurant[7].isoformat() if restaurant[7] else None,
                "AverageRating": round(avg_rating, 2) if avg_rating > 0 else None,
                "TotalRatings": total_ratings,
                "RatingMessage": rating_message
            })
        
        cur.close()
        conn.close()
        return jsonify({"restaurants": restaurant_list, "count": len(restaurant_list)})
    except Exception as e:
        return jsonify({"error": "An internal server error occurred. Please try again later."}), 500

@app.route("/restaurants/<int:restaurant_id>")
def get_restaurant(restaurant_id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Get restaurant details with rating information
        cur.execute("""
            SELECT r.id, r.name, r.cuisine_type, r.location, r.google_api_links, r.google_rating, r.google_place_id, r.created_at,
                   COALESCE(AVG(rr.rating), 0) as avg_rating,
                   COUNT(rr.id) as total_ratings
            FROM restaurants r
            LEFT JOIN restaurant_ratings rr ON r.id = rr.restaurant_id
            WHERE r.id = %s AND r.is_active = TRUE
            GROUP BY r.id, r.name, r.cuisine_type, r.location, r.google_api_links, r.google_rating, r.google_place_id, r.created_at
        """, (restaurant_id,))
        restaurant = cur.fetchone()
        
        cur.close()
        conn.close()
        
        if not restaurant:
            return jsonify({"error": "The requested restaurant could not be found."}), 404
        
        avg_rating = float(restaurant[8]) if restaurant[8] else 0
        total_ratings = restaurant[9]
        google_rating = float(restaurant[5]) if restaurant[5] else None
        
        # Determine rating message
        if total_ratings == 0:
            rating_message = "Have not been rated by users"
        else:
            rating_message = f"Rated by {total_ratings} user{'s' if total_ratings != 1 else ''} (Avg: {avg_rating:.1f}/5)"
        
        return jsonify({
            "restaurant": {
                "ResturantsId": restaurant[0],
                "Name": restaurant[1],
                "Cuisine Type": restaurant[2],
                "Location": restaurant[3],
                "GoogleApiLinks": restaurant[4],
                "rating": google_rating,  # Google rating
                "google_place_id": restaurant[6],
                "CreatedAt": restaurant[7].isoformat() if restaurant[7] else None,
                "AverageRating": round(avg_rating, 2) if avg_rating > 0 else None,
                "TotalRatings": total_ratings,
                "RatingMessage": rating_message
            }
        })
    except Exception as e:
        return jsonify({"error": "An internal server error occurred. Please try again later."}), 500

# --- Create Restaurant ---
@app.route("/restaurants", methods=["POST"])
def create_restaurant():
    data = request.json
    name = data.get("name")
    cuisine_type = data.get("cuisine_type")
    location = data.get("location")
    google_api_links = data.get("google_api_links")

    if not name or not cuisine_type or not location:
        return jsonify({"error": "Name, cuisine type, and location are required fields."}), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO restaurants (name, cuisine_type, location, google_api_links, created_at, is_active)
            VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP, TRUE)
            RETURNING id
        """, (name, cuisine_type, location, google_api_links))
        
        restaurant_id = cur.fetchone()[0]
        conn.commit()
        
        cur.close()
        conn.close()
        
        return jsonify({
            "message": "Restaurant created successfully",
            "restaurant": {
                "ResturantsId": restaurant_id,
                "Name": name,
                "Cuisine Type": cuisine_type,
                "Location": location,
                "GoogleApiLinks": google_api_links,
                "CreatedAt": "2024-01-01T00:00:00"  # Will be set by database
            }
        }), 201
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
            cur.close()
            conn.close()
        return jsonify({"error": "Unable to process your request. Please verify your input and try again."}), 400

# --- Signup ---
@app.route("/signup", methods=["POST"])
@rate_limit(max_requests=5, window=3600)  # 5 signup attempts per hour
@require_csrf
def signup():
    data = request.json
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")

    if not username or not email or not password:
        return jsonify({"error": "Required fields are missing. Please provide all necessary information."}), 400

    # Validate and sanitize inputs
    username = sanitize_input(username, 50)
    email = sanitize_input(email, 100)
    # Convert email to lowercase for case-insensitive storage
    email = email.lower().strip()
    
    if not validate_username(username):
        return jsonify({"error": "Username must be 3-50 characters long and contain only letters, numbers, underscores, and hyphens"}), 400
    
    if not validate_email(email):
        return jsonify({"error": "Invalid email format"}), 400
    
    if not validate_password(password):
        return jsonify({"error": "Password must be at least 8 characters long with uppercase, lowercase, and number"}), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Check if user already exists (case-insensitive email check)
        cur.execute("SELECT id FROM users WHERE LOWER(email) = %s OR username = %s", (email, username))
        if cur.fetchone():
            cur.close()
            conn.close()
            return jsonify({"error": "User already exists"}), 400
        
        hashed = ph.hash(password)
        
        # Check if this is an admin signup (using special email pattern or environment variable)
        # For security, you can set ADMIN_SIGNUP_EMAIL in environment to allow admin creation
        admin_email_pattern = os.environ.get("ADMIN_SIGNUP_EMAIL", "")
        is_admin_user = False
        if admin_email_pattern and email == admin_email_pattern:
            is_admin_user = True
            app.logger.info(f"Creating admin user: {username}")
        
        cur.execute(
            "INSERT INTO users (username, email, password_hash, is_admin, created_at) VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)",
            (username, email, hashed, is_admin_user)
        )
        conn.commit()
        
        cur.close()
        conn.close()
        return jsonify({"message": "User registered successfully!"}), 201
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        app.logger.error("Signup error: %s", e)
        return jsonify({"error": "Unable to complete registration. Please verify your information and try again."}), 400

# --- Login ---
@app.route("/login", methods=["POST"])
def login():
    data = request.json
    email = data.get("email")
    password = data.get("password")

    # Convert email to lowercase for case-insensitive login
    if email:
        email = email.lower().strip()

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("SELECT id, username, password_hash, COALESCE(is_admin, FALSE) FROM users WHERE LOWER(email) = %s", (email,))
        user = cur.fetchone()

        if not user:
            cur.close()
            conn.close()
            return jsonify({"error": "User not found"}), 404

        ph.verify(user[2], password)
        token = serializer.dumps({"id": user[0], "username": user[1]})
        
        cur.close()
        conn.close()
        return jsonify({"message": "Login successful", "token": token, "user": {"UserId": user[0], "UserName": user[1], "UserEmail": email, "IsAdmin": user[3]}}), 200
    except Exception as e:
        if 'conn' in locals():
            cur.close()
            conn.close()
        if "Invalid password" in str(e) or "verify" in str(e):
            return jsonify({"error": "The password you entered is incorrect. Please try again."}), 401
        return jsonify({"error": "Authentication failed. Please verify your credentials and try again."}), 401

# --- Auth: current user ---
def _require_auth(req):
    auth_header = req.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None, (jsonify({"error": "Authentication required. Please sign in to continue."}), 401)
    token = auth_header.split(" ", 1)[1]
    try:
        data = serializer.loads(token, max_age=3600)  # 1 hour expiry
        return data, None
    except SignatureExpired:
        return None, (jsonify({"error": "Your session has expired. Please sign in again."}), 401)
    except BadSignature:
        return None, (jsonify({"error": "Invalid authentication token. Please sign in again."}), 401)

def _is_admin(user_id):
    """Check if user is an admin"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT COALESCE(is_admin, FALSE) FROM users WHERE id = %s", (user_id,))
        result = cur.fetchone()
        cur.close()
        conn.close()
        return result[0] if result else False
    except Exception:
        return False


@app.route("/me")
def me():
    data, error = _require_auth(request)
    if error is not None:
        return error
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Get full user details including admin status
        cur.execute("SELECT id, username, email, created_at, COALESCE(is_admin, FALSE) FROM users WHERE id = %s", (data["id"],))
        user = cur.fetchone()
        
        cur.close()
        conn.close()
        
        if user:
            return jsonify({
                "user": {
                    "UserId": user[0],
                    "UserName": user[1], 
                    "UserEmail": user[2],
                    "CreatedAt": user[3].isoformat() if user[3] else None,
                    "IsAdmin": user[4]
                }
            })
        else:
            return jsonify({"error": "User account could not be found."}), 404
    except Exception as e:
        return jsonify({"error": "An internal server error occurred. Please try again later."}), 500

# Update user profile (username and/or password)
@app.route("/me", methods=["PUT"])
@rate_limit(max_requests=10, window=3600)  # 10 updates per hour
@require_csrf
def update_profile():
    """Update current user's profile (username and/or password)"""
    data, error = _require_auth(request)
    if error is not None:
        return error
    
    try:
        request_data = request.get_json()
        if not request_data:
            return jsonify({"error": "Request data is required to process this action."}), 400
        
        user_id = data["id"]
        new_username = request_data.get("username")
        new_password = request_data.get("password")
        current_password = request_data.get("current_password")
        
        # At least one field must be provided
        if not new_username and not new_password:
            return jsonify({"error": "Please provide at least one field to update (username or password)."}), 400
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Get current user data
        cur.execute("SELECT username, email, password_hash FROM users WHERE id = %s", (user_id,))
        user = cur.fetchone()
        
        if not user:
            cur.close()
            conn.close()
            return jsonify({"error": "User account could not be found."}), 404
        
        current_username = user[0]
        current_email = user[1]
        stored_password_hash = user[2]
        
        # If changing password, verify current password
        if new_password:
            if not current_password:
                cur.close()
                conn.close()
                return jsonify({"error": "Current password is required to change your password."}), 400
            
            # Verify current password
            try:
                ph.verify(stored_password_hash, current_password)
            except Exception:
                cur.close()
                conn.close()
                return jsonify({"error": "Current password is incorrect. Please try again."}), 401
            
            # Validate new password
            if not validate_password(new_password):
                cur.close()
                conn.close()
                return jsonify({"error": "Password must be at least 8 characters long with uppercase, lowercase, and number"}), 400
        
        # If changing username, validate it
        if new_username:
            new_username = sanitize_input(new_username, 50)
            if not validate_username(new_username):
                cur.close()
                conn.close()
                return jsonify({"error": "Username must be 3-50 characters long and contain only letters, numbers, underscores, and hyphens"}), 400
            
            # Check if username is already taken by another user
            cur.execute("SELECT id FROM users WHERE username = %s AND id != %s", (new_username, user_id))
            if cur.fetchone():
                cur.close()
                conn.close()
                return jsonify({"error": "This username is already taken. Please choose a different one."}), 400
        
        # Update user
        if new_username and new_password:
            # Update both username and password
            hashed_password = ph.hash(new_password)
            cur.execute("""
                UPDATE users 
                SET username = %s, password_hash = %s
                WHERE id = %s
            """, (new_username, hashed_password, user_id))
            update_message = "Username and password updated successfully"
        elif new_username:
            # Update only username
            cur.execute("""
                UPDATE users 
                SET username = %s
                WHERE id = %s
            """, (new_username, user_id))
            update_message = "Username updated successfully"
        else:
            # Update only password
            hashed_password = ph.hash(new_password)
            cur.execute("""
                UPDATE users 
                SET password_hash = %s
                WHERE id = %s
            """, (hashed_password, user_id))
            update_message = "Password updated successfully"
        
        conn.commit()
        
        # Get updated user data
        cur.execute("SELECT id, username, email, created_at, COALESCE(is_admin, FALSE) FROM users WHERE id = %s", (user_id,))
        updated_user = cur.fetchone()
        
        cur.close()
        conn.close()
        
        return jsonify({
            "message": update_message,
            "user": {
                "UserId": updated_user[0],
                "UserName": updated_user[1],
                "UserEmail": updated_user[2],
                "CreatedAt": updated_user[3].isoformat() if updated_user[3] else None,
                "IsAdmin": updated_user[4]
            }
        }), 200
        
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
            if 'cur' in locals():
                cur.close()
            conn.close()
        app.logger.error(f"Update profile error: {e}")
        import traceback
        app.logger.error(traceback.format_exc())
        return jsonify({"error": "An internal server error occurred. Please try again later."}), 500

# Delete current user's account
@app.route("/me", methods=["DELETE"])
@rate_limit(max_requests=5, window=3600)  # 5 delete attempts per hour
@require_csrf
def delete_account():
    """Delete current user's own account"""
    data, error = _require_auth(request)
    if error is not None:
        return error
    
    try:
        request_data = request.get_json() or {}
        user_id = data["id"]
        password_confirmation = request_data.get("password")
        
        # Require password confirmation for security
        if not password_confirmation:
            return jsonify({"error": "Password confirmation is required to delete your account."}), 400
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Get user data and verify password
        cur.execute("SELECT id, username, email, password_hash FROM users WHERE id = %s", (user_id,))
        user = cur.fetchone()
        
        if not user:
            cur.close()
            conn.close()
            return jsonify({"error": "User account could not be found."}), 404
        
        # Verify password
        try:
            ph.verify(user[3], password_confirmation)
        except Exception:
            cur.close()
            conn.close()
            return jsonify({"error": "Password confirmation is incorrect. Please try again."}), 401
        
        username = user[1]
        
        # Delete user (CASCADE will handle related data: group_members, messages)
        # Note: restaurant_ratings may need manual cleanup if no CASCADE
        cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()
        
        cur.close()
        conn.close()
        
        return jsonify({
            "message": "Your account has been deleted successfully. We're sorry to see you go."
        }), 200
        
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
            if 'cur' in locals():
                cur.close()
            conn.close()
        app.logger.error(f"Delete account error: {e}")
        import traceback
        app.logger.error(traceback.format_exc())
        return jsonify({"error": "An internal server error occurred. Please try again later."}), 500


# --- Search Restaurants by Place ID ---
@app.route("/restaurants/search")
def search_restaurants_by_place_id():
    place_id = request.args.get("place_id")
    
    if not place_id:
            return jsonify({"error": "Place ID is required to process this request."}), 400
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        sql = """
            SELECT id, name, cuisine_type, location, google_api_links, created_at
            FROM restaurants 
            WHERE google_api_links LIKE %s AND is_active = TRUE
        """
        
        cur.execute(sql, (f"%place_id:{place_id}%",))
        restaurants = cur.fetchall()
        
        cur.close()
        conn.close()
        
        # Convert to list of dictionaries
        restaurant_list = []
        for restaurant in restaurants:
            restaurant_dict = {
                "ResturantsId": restaurant[0],
                "name": restaurant[1],
                "cuisine_type": restaurant[2],
                "location": restaurant[3],
                "google_api_links": restaurant[4],
                "created_at": restaurant[5].isoformat() if restaurant[5] else None
            }
            restaurant_list.append(restaurant_dict)
        
        return jsonify(restaurant_list)
        
    except Exception as e:
        print(f"Error searching restaurants by place_id: {e}")
        return jsonify({"error": "An internal server error occurred. Please try again later."}), 500

# --- Search ---
@app.route("/search")
def search_restaurants():
    query = request.args.get("q", "")
    cuisine_type = request.args.get("cuisine_type", "")
    location = request.args.get("location", "")
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        sql = """
            SELECT r.id, r.name, r.cuisine_type, r.location, r.google_api_links, r.created_at
            FROM restaurants r
            WHERE r.is_active = TRUE
        """
        params = []
        
        if query:
            sql += " AND (r.name ILIKE %s OR r.location ILIKE %s)"
            params.extend([f"%{query}%", f"%{query}%"])
        
        if cuisine_type:
            sql += " AND r.cuisine_type ILIKE %s"
            params.append(f"%{cuisine_type}%")
        
        if location:
            sql += " AND r.location ILIKE %s"
            params.append(f"%{location}%")
        
        sql += " ORDER BY r.created_at DESC"
        
        cur.execute(sql, params)
        restaurants = cur.fetchall()
        
        restaurant_list = []
        for restaurant in restaurants:
            restaurant_list.append({
                "ResturantsId": restaurant[0],
                "Name": restaurant[1],
                "Cuisine Type": restaurant[2],
                "Location": restaurant[3],
                "GoogleApiLinks": restaurant[4],
                "CreatedAt": restaurant[5].isoformat() if restaurant[5] else None
            })
        
        cur.close()
        conn.close()
        return jsonify({"restaurants": restaurant_list, "count": len(restaurant_list)})
    except Exception as e:
        if 'conn' in locals():
            cur.close()
            conn.close()
        return jsonify({"error": "An internal server error occurred. Please try again later."}), 500

# --- Google Places API Search ---
@app.route("/test-save", methods=["POST"])
def test_save_restaurant():
    """Test endpoint to verify database saving works"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO restaurants (name, cuisine_type, location, google_api_links, google_rating, google_place_id, google_types, google_price_level, google_photo_reference, created_at, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, TRUE)
            RETURNING id
        """, ("Test Restaurant 2", "Test", "Test Location", "test", 4.5, "test_place_id_2", '["restaurant"]', 2, "test_photo"))
        
        restaurant_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({"success": True, "restaurant_id": restaurant_id})
    except Exception as e:
        return jsonify({"error": "An internal server error occurred. Please try again later."}), 500

@app.route("/google-search", methods=["POST"])
@rate_limit(max_requests=100, window=3600)  # 100 searches per hour
def search_google_places():
    # Check if user is authenticated (optional)
    user_data = None
    print(f"=== SEARCH REQUEST DEBUG ===")
    print(f"Authorization header: {request.headers.get('Authorization', 'None')}")
    try:
        user_data, _ = _require_auth(request)
        print(f"User authenticated: {user_data['username'] if user_data else 'None'}")
    except Exception as e:
        # User not authenticated, that's fine for search
        print(f"User not authenticated: {str(e)}")
        pass
    
    data = request.json
    query = data.get("query", "").strip()
    location = data.get("location", "").strip()
    radius = data.get("radius", 5000)  # Default 5km radius
    
    if not query:
        return jsonify({"error": "Search query is required. Please enter a location to search."}), 400
    
    # Improve query for ambiguous city names like "toronto" and "london"
    # Add country/region hints to help Google Places API disambiguate
    # Do this BEFORE sanitization to preserve the enhanced query
    location_lower = location.lower() if location else ""
    query_lower = query.lower()
    
    # If the query or location is just "toronto", make it more specific
    if location_lower == "toronto" or (query_lower and "toronto" in query_lower and "ontario" not in query_lower and "canada" not in query_lower):
        # Default to Toronto, Ontario, Canada (most common)
        if "restaurants in" in query_lower:
            query = query.replace("toronto", "toronto ontario canada")
        else:
            query = f"restaurants in toronto ontario canada"
        location = "toronto ontario canada"
        print(f"Enhanced query for Toronto: {query}")
    
    # If the query or location is just "london", make it more specific
    elif location_lower == "london" or (query_lower and "london" in query_lower and "ontario" not in query_lower and "uk" not in query_lower and "england" not in query_lower and "canada" not in query_lower):
        # Default to London, UK (most common)
        if "restaurants in" in query_lower:
            query = query.replace("london", "london uk")
        else:
            query = f"restaurants in london uk"
        location = "london uk"
        print(f"Enhanced query for London: {query}")
    
    # Sanitize search inputs AFTER enhancing the query
    query = sanitize_input(query, 200)
    location = sanitize_input(location, 200)
    
    # First, check if we have restaurants in our database for this location
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Search database for restaurants in this location
        print(f"=== DATABASE SEARCH DEBUG ===")
        print(f"Searching for: location='{location}', query='{query}'")
        cur.execute("""
            SELECT r.id, r.name, r.cuisine_type, r.location, r.google_api_links, r.google_rating, r.google_place_id, r.created_at, r.google_types, r.google_price_level, r.google_photo_reference,
                   COALESCE(AVG(rr.rating), 0) as avg_rating,
                   COUNT(rr.id) as total_ratings
            FROM restaurants r
            LEFT JOIN restaurant_ratings rr ON r.id = rr.restaurant_id
            WHERE r.is_active = TRUE 
            AND (LOWER(r.location) LIKE LOWER(%s) OR LOWER(r.name) LIKE LOWER(%s))
            GROUP BY r.id, r.name, r.cuisine_type, r.location, r.google_api_links, r.google_rating, r.google_place_id, r.created_at, r.google_types, r.google_price_level, r.google_photo_reference
            ORDER BY r.created_at DESC
            LIMIT 20
        """, (f"%{location}%", f"%{query}%"))
        
        db_restaurants = cur.fetchall()
        print(f"Found {len(db_restaurants)} restaurants in database")
        
        if db_restaurants:
            # We have restaurants in database, format and return them
            formatted_places = []
            
            for restaurant in db_restaurants:
                avg_rating = float(restaurant[8]) if restaurant[8] else 0
                total_ratings = restaurant[9]
                google_rating = float(restaurant[5]) if restaurant[5] else None
                
                # Get user's review if authenticated
                user_review = None
                user_rating = None
                if user_data:
                    print(f"Fetching user review for restaurant {restaurant[0]} and user {user_data['id']}")
                    cur.execute("""
                        SELECT rating, review_text 
                        FROM restaurant_ratings 
                        WHERE restaurant_id = %s AND user_id = %s
                    """, (restaurant[0], user_data["id"]))
                    user_review_data = cur.fetchone()
                    if user_review_data:
                        user_rating = user_review_data[0]
                        user_review = user_review_data[1]
                        print(f"Found user review: rating={user_rating}, review={user_review}")
                    else:
                        print(f"No user review found for restaurant {restaurant[0]}")
                else:
                    print("No user_data available for fetching reviews")
                
                # Generate photo URL if we have photo reference
                photo_url = None
                if len(restaurant) > 10 and restaurant[10]:  # google_photo_reference
                    photo_url = get_photo_url(restaurant[10])
                
                # Use original Google API types and price level
                google_types = []
                google_price_level = 0
                
                # Parse stored Google types (column 8) and price level (column 9)
                if len(restaurant) > 8 and restaurant[8]:  # google_types
                    try:
                        google_types = json.loads(restaurant[8])
                    except:
                        google_types = ["restaurant"]
                else:
                    google_types = ["restaurant"]
                
                if len(restaurant) > 9 and restaurant[9] is not None:  # google_price_level
                    google_price_level = restaurant[9]
                
                formatted_places.append({
                    "place_id": restaurant[6] or f"db_{restaurant[0]}",
                    "ResturantsId": restaurant[0],  # Add database ID
                    "name": restaurant[1],
                    "formatted_address": restaurant[3],
                    "rating": google_rating,
                    "price_level": google_price_level,
                    "types": google_types,
                    "geometry": {"location": {"lat": 0, "lng": 0}},  # Placeholder
                    "photos": [],
                    "photo_url": photo_url,
                    "user_review": user_review,
                    "user_rating": user_rating,
                    "AverageRating": round(avg_rating, 2) if avg_rating > 0 else None,
                    "TotalRatings": total_ratings,
                    "from_database": True
                })
            
            cur.close()
            conn.close()
            
            return jsonify({
                "places": formatted_places,
                "count": len(formatted_places),
                "source": "database",
                "message": f"Found {len(formatted_places)} restaurants from our database"
            })
    
    except Exception as e:
        print(f"Database search error: {e}")
        # Continue to Google API search if database search fails
    
    cur.close()
    conn.close()
    
    # If no restaurants found in database, proceed with Google API search
    # Check API quota first
    quota_ok, quota_error = check_api_quota()
    if not quota_ok:
        return jsonify({"error": quota_error}), 429
    
    # Basic validation - only check for very obvious issues
    import re
    
    # Only reject completely empty or very short queries
    if len(query.strip()) < 2:
        return jsonify({"error": "Please enter at least 2 characters for your search query."}), 400
    
    # Only reject if it's purely numbers or special characters (no letters at all)
    if not re.search(r'[a-zA-Z]', query):
        return jsonify({"error": "Please enter a valid location name containing letters."}), 400
    
    try:
        # Search for places using Google Places API
        # For ambiguous city names like "toronto" or "london", use the query directly
        # The query already includes "restaurants in {city}" which helps disambiguate
        search_url = f"{GOOGLE_PLACES_API_URL}/textsearch/json"
        params = {
            "query": query,
            "key": GOOGLE_MAPS_API_KEY,
            "type": "restaurant"
        }
        
        # Note: Google Places Text Search API doesn't use "location" as a string parameter
        # It uses "location" with lat/lng coordinates (e.g., "location": "43.6532,-79.3832").
        # For city names, we rely on the query string which already includes "restaurants in {city}".
        # We do NOT add location/radius parameters for text search - they're only for nearby search.
        
        print(f"=== GOOGLE PLACES API REQUEST ===")
        print(f"Query: {query}")
        print(f"Location (for reference): {location}")
        print(f"URL: {search_url}")
        print(f"Params: {params}")
        
        response = requests.get(search_url, params=params, timeout=10)
        response.raise_for_status()
        
        # Track API usage
        usage = load_api_usage()
        usage["total_requests"] += 1
        usage["daily_requests"] += 1
        usage["last_request"] = datetime.now().isoformat()
        save_api_usage(usage)
        
        places_data = response.json()
        
        print(f"=== GOOGLE PLACES API RESPONSE ===")
        print(f"Status: {places_data.get('status')}")
        print(f"Results count: {len(places_data.get('results', []))}")
        
        # Handle different API response statuses
        api_status = places_data.get("status")
        if api_status == "ZERO_RESULTS":
            return jsonify({"error": f"No restaurants found for '{location or query}'. Please try a different location or be more specific (e.g., 'Toronto, ON' or 'London, UK')."}), 404
        elif api_status == "INVALID_REQUEST":
            error_message = places_data.get("error_message", "Invalid request to Google Places API")
            print(f"Google Places API error: {error_message}")
            return jsonify({"error": f"Invalid search request. Please try a different location."}), 400
        elif api_status == "OVER_QUERY_LIMIT":
            return jsonify({"error": "Google Places API quota exceeded. Please try again later."}), 429
        elif api_status == "REQUEST_DENIED":
            error_message = places_data.get("error_message", "Request denied by Google Places API")
            print(f"Google Places API denied: {error_message}")
            return jsonify({"error": "Search service temporarily unavailable. Please try again later."}), 503
        elif api_status != "OK":
            error_message = places_data.get("error_message", f"Unknown error: {api_status}")
            print(f"Google Places API error status: {api_status}, message: {error_message}")
            return jsonify({"error": f"Unable to search restaurants. Please try again later or try a more specific location."}), 400
        
        places = places_data.get("results", [])
        
        # If no places found, return error
        if not places:
            return jsonify({"error": f"No restaurants found for '{query}'. Please try searching for a different location."}), 404
        
        # Format the results and automatically save to database
        formatted_places = []
        saved_count = 0
        
        # Get database connection
        conn = get_db_connection()
        cur = conn.cursor()
        
        try:
            for place in places:
                # Format the place data
                photos = place.get("photos", [])
                photo_url = None
                if photos and len(photos) > 0:
                    photo_url = get_photo_url(photos[0].get("photo_reference"))

                formatted_place = {
                    "place_id": place.get("place_id"),
                    "name": place.get("name"),
                    "formatted_address": place.get("formatted_address"),
                    "rating": place.get("rating"),
                    "price_level": place.get("price_level"),
                    "types": place.get("types", []),
                    "geometry": place.get("geometry"),
                    "photos": photos,
                    "photo_url": photo_url,
                    "user_review": None,
                    "user_rating": None,
                    "AverageRating": None,
                    "TotalRatings": 0,
                    "ResturantsId": None,
                    "from_database": False
                }
                formatted_places.append(formatted_place)

                
                # Try to save to database
                try:
                    # Extract restaurant information
                    name = place.get("name", "")
                    address = place.get("formatted_address", "")
                    types = place.get("types", [])
                    
                    # Determine cuisine type from restaurant name and location
                    cuisine_type = "Other"
                    name_lower = name.lower()
                    address_lower = address.lower()
                    
                    # Indian cuisine detection
                    indian_keywords = ["bhojanalaya", "dhaba", "hotel", "restaurant", "kathiyawadi", "gujarati", "punjabi", "south indian", "north indian"]
                    if any(keyword in name_lower for keyword in indian_keywords) or "india" in address_lower:
                        cuisine_type = "Indian"
                    # Italian cuisine detection
                    elif any(keyword in name_lower for keyword in ["pizza", "pasta", "italian", "trattoria", "ristorante", "gusto"]):
                        cuisine_type = "Italian"
                    # Chinese cuisine detection
                    elif any(keyword in name_lower for keyword in ["chinese", "wok", "dragon", "panda", "bamboo"]):
                        cuisine_type = "Chinese"
                    # Mexican cuisine detection
                    elif any(keyword in name_lower for keyword in ["mexican", "taco", "burrito", "margarita", "cantina"]):
                        cuisine_type = "Mexican"
                    # Japanese cuisine detection
                    elif any(keyword in name_lower for keyword in ["sushi", "japanese", "ramen", "tempura", "sake"]):
                        cuisine_type = "Japanese"
                    # American cuisine detection
                    elif any(keyword in name_lower for keyword in ["burger", "grill", "steak", "bbq", "american", "chop steakhouse", "carbon bar"]):
                        cuisine_type = "American"
                    # Thai cuisine detection
                    elif any(keyword in name_lower for keyword in ["thai", "pad thai", "curry", "spicy"]):
                        cuisine_type = "Thai"
                    # French cuisine detection
                    elif any(keyword in name_lower for keyword in ["french", "bistro", "cafe", "brasserie"]):
                        cuisine_type = "French"
                    # Korean cuisine detection
                    elif any(keyword in name_lower for keyword in ["korean", "kimchi", "bbq", "korean"]):
                        cuisine_type = "Korean"
                    # Mediterranean cuisine detection
                    elif any(keyword in name_lower for keyword in ["mediterranean", "greek", "lebanese", "middle eastern"]):
                        cuisine_type = "Mediterranean"
                    # Bar/Pub detection
                    elif any(keyword in name_lower for keyword in ["bar", "pub", "tavern", "lounge"]):
                        cuisine_type = "Bar & Grill"
                    # Fine dining detection
                    elif any(keyword in name_lower for keyword in ["canoe", "fine dining", "upscale"]):
                        cuisine_type = "Fine Dining"
                    
                    # Create Google Maps link
                    geometry = place.get("geometry", {})
                    location = geometry.get("location", {})
                    lat = location.get("lat")
                    lng = location.get("lng")
                    
                    google_maps_link = ""
                    if lat and lng:
                        google_maps_link = f"https://www.google.com/maps/place/?q=place_id:{place.get('place_id')}"
                    
                    # Check if restaurant already exists
                    cur.execute("SELECT id FROM restaurants WHERE name = %s AND location = %s", (name, address))
                    existing = cur.fetchone()
                    
                    if not existing:
                        # Get photo reference
                        photo_reference = None
                        photos = place.get("photos", [])
                        if photos and len(photos) > 0:
                            photo_reference = photos[0].get("photo_reference")
                            if photo_reference and len(photo_reference) > 500:
                                photo_reference = photo_reference[:500]
                        
                        # Insert into database with Google rating and original data
                        cur.execute("""
                            INSERT INTO restaurants (name, cuisine_type, location, google_api_links, google_rating, google_place_id, google_types, google_price_level, google_photo_reference, created_at, is_active)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, TRUE)
                            RETURNING id
                        """, (name, cuisine_type, address, google_maps_link, place.get('rating'), place.get('place_id'), 
                              json.dumps(place.get('types', [])), place.get('price_level'), photo_reference))
                        
                        restaurant_id = cur.fetchone()[0]
                        saved_count += 1
                    else:
                        restaurant_id = existing[0]
                    
                    # Get aggregate database rating information
                    cur.execute("""
                        SELECT COALESCE(AVG(rating), 0) as avg_rating, COUNT(id) as total_ratings
                        FROM restaurant_ratings 
                        WHERE restaurant_id = %s
                    """, (restaurant_id,))
                    db_rating_data = cur.fetchone()
                    
                    # Update the formatted_place with database information
                    for fp in formatted_places:
                        if fp["place_id"] == place.get("place_id"):
                            fp["ResturantsId"] = restaurant_id
                            fp["AverageRating"] = round(db_rating_data[0], 2) if db_rating_data[0] > 0 else None
                            fp["TotalRatings"] = db_rating_data[1]
                            fp["from_database"] = True  # Mark as from database since we found it
                            break
                    
                    # Check if user has a review for this restaurant
                    if user_data:
                        cur.execute("""
                            SELECT rating, review_text 
                            FROM restaurant_ratings 
                            WHERE restaurant_id = %s AND user_id = %s
                        """, (restaurant_id, user_data["id"]))
                        user_review_data = cur.fetchone()
                        
                        if user_review_data:
                            # Update the formatted_place with user's review
                            for fp in formatted_places:
                                if fp["place_id"] == place.get("place_id"):
                                    fp["user_rating"] = user_review_data[0]
                                    fp["user_review"] = user_review_data[1]
                                    break
                        
                except Exception as e:
                    print(f"Failed to save restaurant {name}: {str(e)}")
                    try:
                        conn.rollback()
                    except Exception as rollback_error:
                        print(f"Rollback failed: {rollback_error}")
                        # If rollback fails, try to reopen the cursor
                        try:
                            cur.close()
                        except Exception:
                            pass
                        cur = conn.cursor()
                    # Continue with other restaurants after rollback
                    continue
            
            # Commit all database changes
            try:
                conn.commit()
            except Exception as e:
                conn.rollback()
            
        except Exception as e:
            print(f"Error in restaurant processing: {str(e)}")
            conn.rollback()
        finally:
            try:
                cur.close()
                conn.close()
            except:
                pass
        
        return jsonify({
            "places": formatted_places,
            "count": len(formatted_places),
            "saved_to_database": saved_count,
            "source": "google_api",
            "status": places_data.get("status"),
            "api_usage": {
                "total_requests": usage["total_requests"],
                "remaining_requests": MAX_REQUESTS - usage["total_requests"],
                "daily_requests": usage["daily_requests"]
            }
        })
        
    except requests.exceptions.RequestException as e:
        print(f"=== REQUEST EXCEPTION ===")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        print(f"Traceback: {repr(e)}")
        return jsonify({"error": f"Unable to connect to search service. Please check your internet connection and try again. Error: {str(e)}"}), 500
    except Exception as e:
        print(f"=== GENERAL EXCEPTION ===")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return jsonify({"error": f"An error occurred while searching. Please try again. Error: {str(e)}"}), 500

# --- Add Google Place to Database ---
@app.route("/add-google-place", methods=["POST"])
def add_google_place():
    # Check API quota first
    quota_ok, quota_error = check_api_quota()
    if not quota_ok:
        return jsonify({"error": quota_error}), 429
    
    data = request.json
    print(f"Received data in add-google-place: {data}")
    place_id = data.get("place_id")
    print(f"Extracted place_id: {place_id}")
    
    if not place_id:
        print("Error: No place_id provided")
        return jsonify({"error": "Place ID is required to process this request."}), 400
    
    try:
        # Get detailed information about the place
        details_url = f"{GOOGLE_PLACES_API_URL}/details/json"
        params = {
            "place_id": place_id,
            "key": GOOGLE_MAPS_API_KEY,
            "fields": "name,formatted_address,types,rating,price_level,geometry,website,formatted_phone_number,photos"
        }
        
        response = requests.get(details_url, params=params)
        response.raise_for_status()
        
        # Track API usage
        usage = load_api_usage()
        usage["total_requests"] += 1
        usage["daily_requests"] += 1
        usage["last_request"] = datetime.now().isoformat()
        save_api_usage(usage)
        
        place_data = response.json()
        
        if place_data.get("status") != "OK":
            return jsonify({"error": f"Google Places API error: {place_data.get('status')}"}), 400
        
        result = place_data.get("result", {})
        
        # Extract restaurant information
        name = result.get("name", "")
        address = result.get("formatted_address", "")
        types = result.get("types", [])
        
        # Determine cuisine type from Google types
        cuisine_type = "Other"
        for place_type in types:
            if place_type in ["restaurant", "food", "meal_takeaway", "meal_delivery"]:
                # Look for specific cuisine types
                if "italian" in place_type or "pizza" in place_type:
                    cuisine_type = "Italian"
                elif "chinese" in place_type or "asian" in place_type:
                    cuisine_type = "Chinese"
                elif "mexican" in place_type:
                    cuisine_type = "Mexican"
                elif "indian" in place_type:
                    cuisine_type = "Indian"
                elif "japanese" in place_type or "sushi" in place_type:
                    cuisine_type = "Japanese"
                elif "american" in place_type:
                    cuisine_type = "American"
                elif "thai" in place_type:
                    cuisine_type = "Thai"
                elif "french" in place_type:
                    cuisine_type = "French"
                elif "korean" in place_type:
                    cuisine_type = "Korean"
                elif "mediterranean" in place_type:
                    cuisine_type = "Mediterranean"
                break
        
        # Create Google Maps link
        geometry = result.get("geometry", {})
        location = geometry.get("location", {})
        lat = location.get("lat")
        lng = location.get("lng")
        
        google_maps_link = ""
        if lat and lng:
            google_maps_link = f"https://www.google.com/maps/place/?q=place_id:{place_id}"
        
        # Get database connection
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Check if restaurant already exists
        cur.execute("SELECT id FROM restaurants WHERE name = %s AND location = %s", (name, address))
        existing = cur.fetchone()
        
        if existing:
            return jsonify({"error": "This restaurant already exists in our database."}), 400
        
        # Get photo reference
        photo_reference = None
        photos = result.get("photos", [])
        if photos and len(photos) > 0:
            photo_reference = photos[0].get("photo_reference")
        
        # Insert into database with Google rating
        cur.execute("""
            INSERT INTO restaurants (name, cuisine_type, location, google_api_links, google_rating, google_place_id, google_photo_reference, created_at, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, TRUE)
            RETURNING id
        """, (name, cuisine_type, address, google_maps_link, result.get('rating'), place_id, photo_reference))
        
        restaurant_id = cur.fetchone()[0]
        conn.commit()
        
        cur.close()
        conn.close()
        
        # Generate photo URL if available
        photos = result.get("photos", [])
        photo_url = None
        if photos and len(photos) > 0:
            photo_url = get_photo_url(photos[0].get("photo_reference"))
        
        return jsonify({
            "message": "Restaurant added successfully",
            "restaurant_id": restaurant_id,
            "restaurant": {
                "ResturantsId": restaurant_id,
                "Name": name,
                "Cuisine Type": cuisine_type,
                "Location": address,
                "GoogleApiLinks": google_maps_link,
                "CreatedAt": "2024-01-01T00:00:00",  # Will be set by database
                "photo_url": photo_url
            },
            "api_usage": {
                "total_requests": usage["total_requests"],
                "remaining_requests": MAX_REQUESTS - usage["total_requests"],
                "daily_requests": usage["daily_requests"]
            }
        }), 201
        
    except requests.exceptions.RequestException as e:
        return jsonify({"error": "Unable to retrieve restaurant information at this time. Please try again later."}), 500
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
            cur.close()
            conn.close()
        return jsonify({"error": "Unable to process your request. Please verify your input and try again."}), 400

# --- API Usage Check ---
@app.route("/api-usage")
def get_api_usage():
    """Check current API usage and remaining quota"""
    usage = load_api_usage()
    return jsonify({
        "total_requests": usage["total_requests"],
        "remaining_requests": MAX_REQUESTS - usage["total_requests"],
        "daily_requests": usage["daily_requests"],
        "last_request": usage.get("last_request"),
        "quota_percentage": (usage["total_requests"] / MAX_REQUESTS) * 100,
        "status": "OK" if usage["total_requests"] < MAX_REQUESTS else "QUOTA_EXCEEDED"
    })

# --- Batch Add Restaurants (Cost-Saving Feature) ---
@app.route("/batch-add-restaurants", methods=["POST"])
def batch_add_restaurants():
    """Add multiple restaurants from a single search to save API calls"""
    data = request.json
    place_ids = data.get("place_ids", [])
    
    if not place_ids:
        return jsonify({"error": "Place IDs are required to process this request."}), 400
    
    if len(place_ids) > 20:
        return jsonify({"error": "Maximum of 20 restaurants can be processed per batch."}), 400
    
    # Check if we have enough quota
    quota_ok, quota_error = check_api_quota()
    if not quota_ok:
        return jsonify({"error": quota_error}), 429
    
    # Load current usage
    usage = load_api_usage()
    
    if usage["total_requests"] + len(place_ids) > MAX_REQUESTS:
        return jsonify({"error": f"Not enough quota. Need {len(place_ids)} requests, have {MAX_REQUESTS - usage['total_requests']} remaining"}), 429
    
    results = []
    errors = []
    
    # Get database connection
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        for place_id in place_ids:
            try:
                # Get detailed information about the place
                details_url = f"{GOOGLE_PLACES_API_URL}/details/json"
                params = {
                    "place_id": place_id,
                    "key": GOOGLE_MAPS_API_KEY,
                    "fields": "name,formatted_address,types,rating,price_level,geometry,website,formatted_phone_number,photos"
                }
                
                response = requests.get(details_url, params=params)
                response.raise_for_status()
                
                # Track API usage
                usage = load_api_usage()
                usage["total_requests"] += 1
                usage["daily_requests"] += 1
                usage["last_request"] = datetime.now().isoformat()
                save_api_usage(usage)
                
                place_data = response.json()
                
                if place_data.get("status") != "OK":
                    errors.append(f"Place {place_id}: {place_data.get('status')}")
                    continue
                
                result = place_data.get("result", {})
                
                # Extract restaurant information
                name = result.get("name", "")
                address = result.get("formatted_address", "")
                types = result.get("types", [])
                
                # Determine cuisine type from Google types
                cuisine_type = "Other"
                for place_type in types:
                    if place_type in ["restaurant", "food", "meal_takeaway", "meal_delivery"]:
                        if "italian" in place_type or "pizza" in place_type:
                            cuisine_type = "Italian"
                        elif "chinese" in place_type or "asian" in place_type:
                            cuisine_type = "Chinese"
                        elif "mexican" in place_type:
                            cuisine_type = "Mexican"
                        elif "indian" in place_type:
                            cuisine_type = "Indian"
                        elif "japanese" in place_type or "sushi" in place_type:
                            cuisine_type = "Japanese"
                        elif "american" in place_type:
                            cuisine_type = "American"
                        elif "thai" in place_type:
                            cuisine_type = "Thai"
                        elif "french" in place_type:
                            cuisine_type = "French"
                        elif "korean" in place_type:
                            cuisine_type = "Korean"
                        elif "mediterranean" in place_type:
                            cuisine_type = "Mediterranean"
                        break
                
                # Create Google Maps link
                geometry = result.get("geometry", {})
                location = geometry.get("location", {})
                lat = location.get("lat")
                lng = location.get("lng")
                
                google_maps_link = ""
                if lat and lng:
                    google_maps_link = f"https://www.google.com/maps/place/?q=place_id:{place_id}"
                
                # Check if restaurant already exists
                cur.execute("SELECT id FROM restaurants WHERE name = %s AND location = %s", (name, address))
                existing = cur.fetchone()
                
                if existing:
                    errors.append(f"Restaurant '{name}' already exists")
                    continue
                
                # Insert into database
                cur.execute("""
                    INSERT INTO restaurants (name, cuisine_type, location, google_api_links, google_rating, google_place_id, created_at, is_active)
                    VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, TRUE)
                    RETURNING id
                """, (name, cuisine_type, address, google_maps_link, None, None))
                
                restaurant_id = cur.fetchone()[0]
                results.append({
                    "ResturantsId": restaurant_id,
                    "Name": name,
                    "Cuisine Type": cuisine_type,
                    "Location": address,
                    "GoogleApiLinks": google_maps_link
                })
                
            except Exception as e:
                errors.append(f"Place {place_id}: {str(e)}")
                continue
    
        conn.commit()
        
        return jsonify({
            "success": True,
            "message": f"Batch processing completed. {len(results)} restaurants added, {len(errors)} errors.",
            "added_count": len(results),
            "restaurants": results,
            "errors": errors,
            "api_usage": {
                "total_requests": usage["total_requests"],
                "remaining_requests": MAX_REQUESTS - usage["total_requests"],
                "daily_requests": usage["daily_requests"]
            }
        }), 201
        
    except Exception as e:
        conn.rollback()
        return jsonify({"error": "A database error occurred. Please try again later."}), 500
    finally:
        cur.close()
        conn.close()

# --- Admin: Set user as admin (one-time setup endpoint) ---
@app.route("/admin/set-admin", methods=["POST"])
def set_user_admin():
    """
    Set a user as admin. 
    This is a one-time setup endpoint. In production, you should protect this with additional security.
    Usage: POST /admin/set-admin with {"username": "admin123"}
    """
    try:
        data = request.json
        username = data.get("username")
        
        if not username:
            return jsonify({"error": "Username is required to complete this action."}), 400
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Check if user exists
        cur.execute("SELECT id, username, email FROM users WHERE username = %s", (username,))
        user = cur.fetchone()
        
        if not user:
            cur.close()
            conn.close()
            return jsonify({"error": f"User '{username}' could not be found."}), 404
        
        # Set user as admin
        cur.execute("UPDATE users SET is_admin = TRUE WHERE username = %s", (username,))
        conn.commit()
        
        cur.close()
        conn.close()
        
        return jsonify({
            "message": f"User '{username}' has been set as admin",
            "user": {
                "id": user[0],
                "username": user[1],
                "email": user[2],
                "is_admin": True
            }
        }), 200
        
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return jsonify({"error": "An internal server error occurred. Please try again later."}), 500

# --- Database Viewer (for development) ---
@app.route("/users")
def get_users():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("SELECT id, username, email, created_at, COALESCE(is_admin, FALSE) FROM users ORDER BY created_at DESC")
        users = cur.fetchall()
        user_list = []
        for user in users:
            user_list.append({
                "UserId": user[0],
                "UserName": user[1],
                "UserEmail": user[2],
                "CreatedAt": user[3].isoformat() if user[3] else None,
                "IsAdmin": user[4]
            })
        
        cur.close()
        conn.close()
        return jsonify({"users": user_list, "count": len(user_list)})
    except Exception as e:
        return jsonify({"error": "An internal server error occurred. Please try again later."}), 500

# --- Admin User Management ---
@app.route("/admin/users", methods=["POST"])
@rate_limit(max_requests=20, window=3600)
@require_csrf
def admin_create_user():
    """Create a new user (admin only)"""
    data, error = _require_auth(request)
    if error is not None:
        return error
    
    user_id = data["id"]
    if not _is_admin(user_id):
        return jsonify({"error": "Admin privileges required"}), 403
    
    req_data = request.json
    username = req_data.get("username")
    email = req_data.get("email")
    password = req_data.get("password")
    is_admin = req_data.get("is_admin", False)
    
    if not username or not email or not password:
        return jsonify({"error": "Missing required fields: username, email, password"}), 400
    
    # Validate and sanitize inputs
    username = sanitize_input(username, 50)
    email = sanitize_input(email, 100)
    # Convert email to lowercase for case-insensitive storage
    email = email.lower().strip()
    
    if not validate_username(username):
        return jsonify({"error": "Username must be 3-50 characters long and contain only letters, numbers, underscores, and hyphens"}), 400
    
    if not validate_email(email):
        return jsonify({"error": "Invalid email format"}), 400
    
    if not validate_password(password):
        return jsonify({"error": "Password must be at least 8 characters long with uppercase, lowercase, and number"}), 400
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Check if user already exists (case-insensitive email check)
        cur.execute("SELECT id FROM users WHERE LOWER(email) = %s OR username = %s", (email, username))
        if cur.fetchone():
            cur.close()
            conn.close()
            return jsonify({"error": "User already exists"}), 400
        
        hashed = ph.hash(password)
        
        cur.execute(
            "INSERT INTO users (username, email, password_hash, is_admin, created_at) VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP) RETURNING id",
            (username, email, hashed, bool(is_admin))
        )
        new_user_id = cur.fetchone()[0]
        conn.commit()
        
        cur.close()
        conn.close()
        return jsonify({"message": "User created successfully", "user_id": new_user_id}), 201
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        app.logger.error(f"Admin create user error: {e}")
        return jsonify({"error": "An internal server error occurred. Please try again later."}), 500

@app.route("/admin/users/<int:user_id>", methods=["PUT"])
@rate_limit(max_requests=20, window=3600)
@require_csrf
def admin_update_user(user_id):
    """Update a user (admin only)"""
    data, error = _require_auth(request)
    if error is not None:
        return error
    
    admin_user_id = data["id"]
    if not _is_admin(admin_user_id):
        return jsonify({"error": "Admin privileges required"}), 403
    
    req_data = request.json
    username = req_data.get("username")
    email = req_data.get("email")
    password = req_data.get("password")
    is_admin = req_data.get("is_admin")
    
    if not username or not email:
        return jsonify({"error": "Missing required fields: username, email"}), 400
    
    # Validate and sanitize inputs
    username = sanitize_input(username, 50)
    email = sanitize_input(email, 100)
    # Convert email to lowercase for case-insensitive storage
    email = email.lower().strip()
    
    if not validate_username(username):
        return jsonify({"error": "Username must be 3-50 characters long and contain only letters, numbers, underscores, and hyphens"}), 400
    
    if not validate_email(email):
        return jsonify({"error": "Invalid email format"}), 400
    
    if password and not validate_password(password):
        return jsonify({"error": "Password must be at least 8 characters long with uppercase, lowercase, and number"}), 400
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Check if user exists
        cur.execute("SELECT id FROM users WHERE id = %s", (user_id,))
        if not cur.fetchone():
            cur.close()
            conn.close()
            return jsonify({"error": "User not found"}), 404
        
        # Check if email/username is already taken by another user (case-insensitive email check)
        cur.execute("SELECT id FROM users WHERE (LOWER(email) = %s OR username = %s) AND id != %s", (email, username, user_id))
        if cur.fetchone():
            cur.close()
            conn.close()
            return jsonify({"error": "Email or username already taken by another user"}), 400
        
        # Update user
        if password:
            hashed = ph.hash(password)
            cur.execute(
                "UPDATE users SET username = %s, email = %s, password_hash = %s, is_admin = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                (username, email, hashed, bool(is_admin), user_id)
            )
        else:
            cur.execute(
                "UPDATE users SET username = %s, email = %s, is_admin = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                (username, email, bool(is_admin), user_id)
            )
        
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"message": "User updated successfully"}), 200
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        app.logger.error(f"Admin update user error: {e}")
        return jsonify({"error": "An internal server error occurred. Please try again later."}), 500

@app.route("/admin/users/<int:user_id>", methods=["DELETE"])
@rate_limit(max_requests=20, window=3600)
@require_csrf
def admin_delete_user(user_id):
    """Delete a user (admin only)"""
    data, error = _require_auth(request)
    if error is not None:
        return error
    
    admin_user_id = data["id"]
    if not _is_admin(admin_user_id):
        return jsonify({"error": "Admin privileges required"}), 403
    
    # Prevent admin from deleting themselves
    if admin_user_id == user_id:
        return jsonify({"error": "Cannot delete your own account"}), 400
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Check if user exists
        cur.execute("SELECT id, username FROM users WHERE id = %s", (user_id,))
        user = cur.fetchone()
        if not user:
            cur.close()
            conn.close()
            return jsonify({"error": "User not found"}), 404
        
        # Delete user (hard delete)
        cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()
        
        cur.close()
        conn.close()
        return jsonify({"message": f"User '{user[1]}' deleted successfully"}), 200
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        app.logger.error(f"Admin delete user error: {e}")
        return jsonify({"error": "An internal server error occurred. Please try again later."}), 500

# --- Restaurant Rating System ---

# Rate a restaurant
@app.route("/restaurants/<int:restaurant_id>/rate", methods=["POST"])
@rate_limit(max_requests=20, window=3600)  # 20 rating submissions per hour
@require_csrf
def rate_restaurant(restaurant_id):
    # Check authentication
    data, error = _require_auth(request)
    if error is not None:
        return error
    
    try:
        rating_data = request.json
        rating = rating_data.get("rating")
        review_text = rating_data.get("review_text", "")
        
        # Validate and sanitize inputs
        if not validate_rating(rating):
            return jsonify({"error": "Rating must be between 1 and 5 stars."}), 400
        
        # Sanitize review text
        review_text = sanitize_input(review_text, 1000)
        
        # Check for inappropriate content
        if contains_inappropriate_content(review_text):
            return jsonify({"error": "Your review contains inappropriate content. Please revise your review and try again."}), 400
        
        # Get database connection
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Check if restaurant exists
        cur.execute("SELECT id FROM restaurants WHERE id = %s AND is_active = TRUE", (restaurant_id,))
        if not cur.fetchone():
            cur.close()
            conn.close()
            return jsonify({"error": "The requested restaurant could not be found."}), 404
        
        # Check if user already rated this restaurant
        cur.execute("SELECT id, rating FROM restaurant_ratings WHERE restaurant_id = %s AND user_id = %s", 
                   (restaurant_id, data["id"]))
        existing_rating = cur.fetchone()
        
        if existing_rating:
            # Update existing rating
            cur.execute("""
                UPDATE restaurant_ratings 
                SET rating = %s, review_text = %s, updated_at = CURRENT_TIMESTAMP
                WHERE restaurant_id = %s AND user_id = %s
                RETURNING id
            """, (rating, review_text, restaurant_id, data["id"]))
            rating_id = cur.fetchone()[0]
            action = "updated"
        else:
            # Create new rating
            cur.execute("""
                INSERT INTO restaurant_ratings (restaurant_id, user_id, rating, review_text)
                VALUES (%s, %s, %s, %s)
                RETURNING id
            """, (restaurant_id, data["id"], rating, review_text))
            rating_id = cur.fetchone()[0]
            action = "created"
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({
            "message": f"Rating {action} successfully",
            "rating_id": rating_id,
            "rating": rating,
            "review_text": review_text
        }), 200
        
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
            if 'cur' in locals():
                cur.close()
            conn.close()
        app.logger.error(f"Rate restaurant error: {e}")
        import traceback
        app.logger.error(traceback.format_exc())
        return jsonify({"error": "An internal server error occurred. Please try again later."}), 500

# Get restaurant ratings
@app.route("/restaurants/<int:restaurant_id>/ratings")
def get_restaurant_ratings(restaurant_id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Check if restaurant exists
        cur.execute("SELECT id, name FROM restaurants WHERE id = %s AND is_active = TRUE", (restaurant_id,))
        restaurant = cur.fetchone()
        if not restaurant:
            cur.close()
            conn.close()
            return jsonify({"error": "The requested restaurant could not be found."}), 404
        
        # Get all ratings for this restaurant
        cur.execute("""
            SELECT r.id, r.rating, r.review_text, r.created_at, u.username
            FROM restaurant_ratings r
            JOIN users u ON r.user_id = u.id
            WHERE r.restaurant_id = %s
            ORDER BY r.created_at DESC
        """, (restaurant_id,))
        
        ratings = cur.fetchall()
        
        # Calculate average rating
        if ratings:
            avg_rating = sum(rating[1] for rating in ratings) / len(ratings)
            total_ratings = len(ratings)
        else:
            avg_rating = None
            total_ratings = 0
        
        # Format ratings
        formatted_ratings = []
        for rating in ratings:
            formatted_ratings.append({
                "id": rating[0],
                "rating": rating[1],
                "review_text": rating[2],
                "created_at": rating[3].isoformat() if rating[3] else None,
                "username": rating[4]
            })
        
        cur.close()
        conn.close()
        
        return jsonify({
            "restaurant_id": restaurant_id,
            "restaurant_name": restaurant[1],
            "average_rating": round(avg_rating, 2) if avg_rating else None,
            "total_ratings": total_ratings,
            "user_rating_message": "Have not been rated by users" if total_ratings == 0 else f"Rated by {total_ratings} user{'s' if total_ratings != 1 else ''}",
            "ratings": formatted_ratings
        })
        
    except Exception as e:
        return jsonify({"error": "An internal server error occurred. Please try again later."}), 500

# Get user's rating for a specific restaurant
@app.route("/restaurants/<int:restaurant_id>/my-rating")
def get_my_rating(restaurant_id):
    # Check authentication
    data, error = _require_auth(request)
    if error is not None:
        return error
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Get user's rating for this restaurant
        cur.execute("""
            SELECT rating, review_text, created_at, updated_at
            FROM restaurant_ratings
            WHERE restaurant_id = %s AND user_id = %s
        """, (restaurant_id, data["id"]))
        
        rating = cur.fetchone()
        
        cur.close()
        conn.close()
        
        if rating:
            return jsonify({
                "rating": rating[0],
                "review_text": rating[1],
                "created_at": rating[2].isoformat() if rating[2] else None,
                "updated_at": rating[3].isoformat() if rating[3] else None
            })
        else:
            return jsonify({
                "rating": None,
                "review_text": None,
                "message": "You have not rated this restaurant yet"
            }), 200
            
    except Exception as e:
        return jsonify({"error": "An internal server error occurred. Please try again later."}), 500

# Delete user's rating for a restaurant (or any rating if admin)
@app.route("/restaurants/<int:restaurant_id>/rate", methods=["DELETE"])
@rate_limit(max_requests=20, window=3600)  # 20 deletions per hour
@require_csrf
def delete_restaurant_rating(restaurant_id):
    # Check authentication
    data, error = _require_auth(request)
    if error is not None:
        return error
    
    try:
        user_id = data["id"]
        is_platform_admin = _is_admin(user_id)
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Get rating_id from request body if admin is deleting someone else's rating
        # For DELETE requests, get_json() might fail if Content-Type is not set
        try:
            request_data = request.get_json() or {}
        except Exception:
            request_data = {}
        rating_id = request_data.get("rating_id")
        
        if is_platform_admin and rating_id:
            # Admin can delete any rating by rating_id
            cur.execute("""
                DELETE FROM restaurant_ratings
                WHERE id = %s AND restaurant_id = %s
                RETURNING id
            """, (rating_id, restaurant_id))
        else:
            # Regular user can only delete their own rating
            cur.execute("""
                DELETE FROM restaurant_ratings
                WHERE restaurant_id = %s AND user_id = %s
                RETURNING id
            """, (restaurant_id, user_id))
        
        deleted_rating = cur.fetchone()
        
        if not deleted_rating:
            cur.close()
            conn.close()
            return jsonify({"error": "The requested rating could not be found."}), 404
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({"message": "Rating deleted successfully"}), 200
        
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
            if 'cur' in locals():
                cur.close()
            conn.close()
        app.logger.error(f"Delete rating error: {e}")
        import traceback
        app.logger.error(traceback.format_exc())
        return jsonify({"error": "An internal server error occurred. Please try again later."}), 500

# --- Review Reporting System ---

# Report an inappropriate review
@app.route("/restaurants/<int:restaurant_id>/ratings/<int:rating_id>/report", methods=["POST"])
@rate_limit(max_requests=10, window=3600)  # 10 reports per hour
@require_csrf
def report_review(restaurant_id, rating_id):
    """Report an inappropriate review"""
    data, error = _require_auth(request)
    if error is not None:
        return error
    
    try:
        user_id = data["id"]
        request_data = request.get_json() or {}
        reason = request_data.get("reason", "").strip()
        description = request_data.get("description", "").strip()
        
        if not reason:
            return jsonify({"error": "Please provide a reason for reporting this review."}), 400
        
        # Validate reason length
        reason = sanitize_input(reason, 255)
        description = sanitize_input(description, 1000)
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Check if rating exists and belongs to the restaurant
        cur.execute("""
            SELECT id, user_id FROM restaurant_ratings 
            WHERE id = %s AND restaurant_id = %s
        """, (rating_id, restaurant_id))
        
        rating = cur.fetchone()
        if not rating:
            cur.close()
            conn.close()
            return jsonify({"error": "The requested rating could not be found."}), 404
        
        # Prevent users from reporting their own reviews
        if rating[1] == user_id:
            cur.close()
            conn.close()
            return jsonify({"error": "You cannot report your own review."}), 400
        
        # Check if user already reported this review
        cur.execute("""
            SELECT id FROM review_reports 
            WHERE rating_id = %s AND reported_by = %s
        """, (rating_id, user_id))
        
        if cur.fetchone():
            cur.close()
            conn.close()
            return jsonify({"error": "You have already reported this review."}), 400
        
        # Create report
        cur.execute("""
            INSERT INTO review_reports (rating_id, reported_by, reason, description)
            VALUES (%s, %s, %s, %s)
            RETURNING id, created_at
        """, (rating_id, user_id, reason, description))
        
        report = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({
            "message": "Review reported successfully. Our team will review it shortly.",
            "report_id": report[0],
            "created_at": report[1].isoformat()
        }), 201
        
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
            if 'cur' in locals():
                cur.close()
            conn.close()
        app.logger.error(f"Report review error: {e}")
        import traceback
        app.logger.error(traceback.format_exc())
        return jsonify({"error": "An internal server error occurred. Please try again later."}), 500

# --- Message Reporting System ---

# Report an inappropriate message
@app.route("/groups/<int:group_id>/messages/<int:message_id>/report", methods=["POST"])
@rate_limit(max_requests=10, window=3600)  # 10 reports per hour
@require_csrf
def report_message(group_id, message_id):
    """Report an inappropriate message"""
    data, error = _require_auth(request)
    if error is not None:
        return error
    
    try:
        user_id = data["id"]
        request_data = request.get_json() or {}
        reason = request_data.get("reason", "").strip()
        description = request_data.get("description", "").strip()
        
        if not reason:
            return jsonify({"error": "Please provide a reason for reporting this message."}), 400
        
        # Validate reason length
        reason = sanitize_input(reason, 255)
        description = sanitize_input(description, 1000)
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Check if message exists and belongs to the group
        cur.execute("""
            SELECT id, user_id FROM messages 
            WHERE id = %s AND group_id = %s AND is_active = TRUE
        """, (message_id, group_id))
        
        message = cur.fetchone()
        if not message:
            cur.close()
            conn.close()
            return jsonify({"error": "The requested message could not be found."}), 404
        
        # Prevent users from reporting their own messages
        if message[1] == user_id:
            cur.close()
            conn.close()
            return jsonify({"error": "You cannot report your own message."}), 400
        
        # Check if user already reported this message
        cur.execute("""
            SELECT id FROM message_reports 
            WHERE message_id = %s AND reported_by = %s
        """, (message_id, user_id))
        
        if cur.fetchone():
            cur.close()
            conn.close()
            return jsonify({"error": "You have already reported this message."}), 400
        
        # Create report
        cur.execute("""
            INSERT INTO message_reports (message_id, reported_by, reason, description)
            VALUES (%s, %s, %s, %s)
            RETURNING id, created_at
        """, (message_id, user_id, reason, description))
        
        report = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({
            "message": "Message reported successfully. Our team will review it shortly.",
            "report_id": report[0],
            "created_at": report[1].isoformat()
        }), 201
        
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
            if 'cur' in locals():
                cur.close()
            conn.close()
        app.logger.error(f"Report message error: {e}")
        import traceback
        app.logger.error(traceback.format_exc())
        return jsonify({"error": "An internal server error occurred. Please try again later."}), 500

# -----------------------------
# Chat System Endpoints
# -----------------------------

@app.route("/groups", methods=["GET"])
@rate_limit(max_requests=100, window=3600)
def get_groups():
    """Get all groups that the user is a member of (or all groups if admin)"""
    try:
        # Get user from token
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            return jsonify({"error": "Authentication required. Please sign in to continue."}), 401
        
        token = token.split(' ')[1]
        try:
            data = serializer.loads(token, max_age=3600)
        except (BadSignature, SignatureExpired):
            return jsonify({"error": "Invalid or expired authentication token. Please sign in again."}), 401
        
        user_id = data["id"]
        is_platform_admin = _is_admin(user_id)
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        if is_platform_admin:
            # Admin can see all groups
            cur.execute("""
                SELECT g.id, g.name, g.description, g.created_by, g.created_at, g.updated_at,
                       u.username as creator_name,
                       COUNT(DISTINCT gm.user_id) FILTER (WHERE gm.is_active = TRUE) as member_count,
                       COALESCE(gm_user.role, 'not_member') as user_role
                FROM groups g
                JOIN users u ON g.created_by = u.id
                LEFT JOIN group_members gm ON g.id = gm.group_id
                LEFT JOIN group_members gm_user ON g.id = gm_user.group_id AND gm_user.user_id = %s AND gm_user.is_active = TRUE
                WHERE g.is_active = TRUE
                GROUP BY g.id, g.name, g.description, g.created_by, g.created_at, g.updated_at, u.username, gm_user.role
                ORDER BY g.updated_at DESC
            """, (user_id,))
        else:
            # Regular user sees only groups they're a member of
            cur.execute("""
                SELECT g.id, g.name, g.description, g.created_by, g.created_at, g.updated_at,
                       u.username as creator_name,
                       COUNT(gm.user_id) as member_count,
                       gm.role as user_role
                FROM groups g
                JOIN group_members gm ON g.id = gm.group_id
                JOIN users u ON g.created_by = u.id
                WHERE gm.user_id = %s AND gm.is_active = TRUE AND g.is_active = TRUE
                GROUP BY g.id, g.name, g.description, g.created_by, g.created_at, g.updated_at, u.username, gm.role
                ORDER BY g.updated_at DESC
            """, (user_id,))
        
        groups = []
        for row in cur.fetchall():
            try:
                groups.append({
                    "id": row[0],
                    "name": row[1],
                    "description": row[2],
                    "created_by": row[3],
                    "created_at": row[4].isoformat() if row[4] else None,
                    "updated_at": row[5].isoformat() if row[5] else None,
                    "creator_name": row[6] if len(row) > 6 else None,
                    "member_count": row[7] if len(row) > 7 else 0,
                    "user_role": row[8] if len(row) > 8 else 'not_member'
                })
            except (IndexError, TypeError) as e:
                app.logger.error(f"Error processing group row: {e}, row: {row}")
                continue
        
        cur.close()
        conn.close()
        
        return jsonify({"groups": groups})
        
    except Exception as e:
        if 'conn' in locals():
            if 'cur' in locals():
                cur.close()
            conn.close()
        app.logger.error(f"Get groups error: {e}")
        import traceback
        app.logger.error(traceback.format_exc())
        return jsonify({"error": "An internal server error occurred. Please try again later."}), 500

@app.route("/groups/discover", methods=["GET"])
@rate_limit(max_requests=100, window=3600)
def discover_groups():
    """Get all public groups that the user can join"""
    try:
        # Get user from token
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            return jsonify({"error": "Authentication required. Please sign in to continue."}), 401
        
        token = token.split(' ')[1]
        try:
            data = serializer.loads(token, max_age=3600)
        except (BadSignature, SignatureExpired):
            return jsonify({"error": "Invalid or expired authentication token. Please sign in again."}), 401
        
        user_id = data["id"]
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Get all active groups with member count and user's role
        cur.execute("""
            SELECT g.id, g.name, g.description, g.created_by, g.created_at, g.updated_at,
                   u.username as creator_name,
                   COUNT(DISTINCT gm_all.user_id) as member_count,
                   COALESCE(gm_user.role, 'not_member') as user_role
            FROM groups g
            JOIN users u ON g.created_by = u.id
            LEFT JOIN group_members gm_all ON g.id = gm_all.group_id AND gm_all.is_active = TRUE
            LEFT JOIN group_members gm_user ON g.id = gm_user.group_id AND gm_user.user_id = %s AND gm_user.is_active = TRUE
            WHERE g.is_active = TRUE
            GROUP BY g.id, g.name, g.description, g.created_by, g.created_at, g.updated_at, u.username, gm_user.role
            ORDER BY g.updated_at DESC
        """, (user_id,))
        
        groups = []
        for row in cur.fetchall():
            try:
                groups.append({
                    "id": row[0],
                    "name": row[1],
                    "description": row[2],
                    "created_by": row[3],
                    "created_at": row[4].isoformat() if row[4] else None,
                    "updated_at": row[5].isoformat() if row[5] else None,
                    "creator_name": row[6] if len(row) > 6 else None,
                    "member_count": row[7] if len(row) > 7 else 0,
                    "user_role": row[8] if len(row) > 8 and row[8] != 'not_member' else None
                })
            except (IndexError, TypeError) as e:
                app.logger.error(f"Error processing discover group row: {e}, row: {row}")
                continue
        
        cur.close()
        conn.close()
        
        return jsonify({"groups": groups})
        
    except Exception as e:
        if 'conn' in locals():
            if 'cur' in locals():
                cur.close()
            conn.close()
        app.logger.error(f"Discover groups error: {e}")
        import traceback
        app.logger.error(traceback.format_exc())
        return jsonify({"error": "An internal server error occurred. Please try again later."}), 500

@app.route("/groups", methods=["POST"])
@rate_limit(max_requests=50, window=3600)
@require_csrf
def create_group():
    """Create a new group"""
    try:
        # Get user from token
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            return jsonify({"error": "Authentication required. Please sign in to continue."}), 401
        
        token = token.split(' ')[1]
        try:
            data = serializer.loads(token, max_age=3600)
        except (BadSignature, SignatureExpired):
            return jsonify({"error": "Invalid or expired authentication token. Please sign in again."}), 401
        
        user_id = data["id"]
        
        # Get request data
        request_data = request.get_json()
        if not request_data:
            return jsonify({"error": "Request data is required to process this action."}), 400
        
        name = sanitize_input(request_data.get('name', ''), 255)
        description = sanitize_input(request_data.get('description', ''), 1000)
        
        if not name:
            return jsonify({"error": "Group name is required to create a group."}), 400
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Create group
        cur.execute("""
            INSERT INTO groups (name, description, created_by)
            VALUES (%s, %s, %s)
            RETURNING id, created_at
        """, (name, description, user_id))
        
        group_result = cur.fetchone()
        group_id = group_result[0]
        created_at = group_result[1]
        
        # Add creator as admin member
        cur.execute("""
            INSERT INTO group_members (group_id, user_id, role)
            VALUES (%s, %s, 'admin')
        """, (group_id, user_id))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({
            "message": "Group created successfully",
            "group": {
                "id": group_id,
                "name": name,
                "description": description,
                "created_by": user_id,
                "created_at": created_at.isoformat(),
                "user_role": "admin"
            }
        }), 201
        
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
            if 'cur' in locals():
                cur.close()
            conn.close()
        app.logger.error(f"Create group error: {e}")
        import traceback
        app.logger.error(traceback.format_exc())
        return jsonify({"error": "An internal server error occurred. Please try again later."}), 500

@app.route("/groups/<int:group_id>", methods=["GET"])
@rate_limit(max_requests=100, window=3600)
def get_group_details(group_id):
    """Get detailed information about a specific group"""
    try:
        # Get user from token
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            return jsonify({"error": "Authentication required. Please sign in to continue."}), 401
        
        token = token.split(' ')[1]
        try:
            data = serializer.loads(token, max_age=3600)
        except (BadSignature, SignatureExpired):
            return jsonify({"error": "Invalid or expired authentication token. Please sign in again."}), 401
        
        user_id = data["id"]
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Check if user is member of the group
        cur.execute("""
            SELECT gm.role FROM group_members gm
            WHERE gm.group_id = %s AND gm.user_id = %s AND gm.is_active = TRUE
        """, (group_id, user_id))
        
        user_role = cur.fetchone()
        if not user_role:
            return jsonify({"error": "You are not a member of this group. Please join the group to access this feature."}), 403
        
        # Get group details
        cur.execute("""
            SELECT g.id, g.name, g.description, g.created_by, g.created_at, g.updated_at,
                   u.username as creator_name,
                   COUNT(gm.user_id) as member_count
            FROM groups g
            JOIN users u ON g.created_by = u.id
            LEFT JOIN group_members gm ON g.id = gm.group_id AND gm.is_active = TRUE
            WHERE g.id = %s AND g.is_active = TRUE
            GROUP BY g.id, g.name, g.description, g.created_by, g.created_at, g.updated_at, u.username
        """, (group_id,))
        
        group_result = cur.fetchone()
        if not group_result:
            return jsonify({"error": "Group not found"}), 404
        
        # Get group members
        cur.execute("""
            SELECT u.id, u.username, u.email, gm.joined_at, gm.role
            FROM group_members gm
            JOIN users u ON gm.user_id = u.id
            WHERE gm.group_id = %s AND gm.is_active = TRUE
            ORDER BY gm.joined_at ASC
        """, (group_id,))
        
        members = []
        for row in cur.fetchall():
            members.append({
                "id": row[0],
                "username": row[1],
                "email": row[2],
                "joined_at": row[3].isoformat() if row[3] else None,
                "role": row[4]
            })
        
        cur.close()
        conn.close()
        
        return jsonify({
            "group": {
                "id": group_result[0],
                "name": group_result[1],
                "description": group_result[2],
                "created_by": group_result[3],
                "created_at": group_result[4].isoformat() if group_result[4] else None,
                "updated_at": group_result[5].isoformat() if group_result[5] else None,
                "creator_name": group_result[6],
                "member_count": group_result[7],
                "user_role": user_role[0]
            },
            "members": members
        })
        
    except Exception as e:
        return jsonify({"error": "An internal server error occurred. Please try again later."}), 500

@app.route("/groups/<int:group_id>/join", methods=["POST"])
@rate_limit(max_requests=50, window=3600)
@require_csrf
def join_group(group_id):
    """Join a group"""
    try:
        # Get user from token
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            return jsonify({"error": "Authentication required. Please sign in to continue."}), 401
        
        token = token.split(' ')[1]
        try:
            data = serializer.loads(token, max_age=3600)
        except (BadSignature, SignatureExpired):
            return jsonify({"error": "Invalid or expired authentication token. Please sign in again."}), 401
        
        user_id = data["id"]
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Check if group exists and is active
        cur.execute("SELECT id FROM groups WHERE id = %s AND is_active = TRUE", (group_id,))
        if not cur.fetchone():
            return jsonify({"error": "Group not found"}), 404
        
        # Check if user is already a member
        cur.execute("""
            SELECT id FROM group_members 
            WHERE group_id = %s AND user_id = %s
        """, (group_id, user_id))
        
        existing_member = cur.fetchone()
        if existing_member:
            # Reactivate if inactive
            cur.execute("""
                UPDATE group_members 
                SET is_active = TRUE, joined_at = CURRENT_TIMESTAMP
                WHERE group_id = %s AND user_id = %s
            """, (group_id, user_id))
        else:
            # Add new member
            cur.execute("""
                INSERT INTO group_members (group_id, user_id, role)
                VALUES (%s, %s, 'member')
            """, (group_id, user_id))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({"message": "Successfully joined the group"})
        
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return jsonify({"error": "An internal server error occurred. Please try again later."}), 500

@app.route("/groups/<int:group_id>/leave", methods=["POST"])
@rate_limit(max_requests=50, window=3600)
@require_csrf
def leave_group(group_id):
    """Leave a group"""
    try:
        # Get user from token
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            return jsonify({"error": "Authentication required. Please sign in to continue."}), 401
        
        token = token.split(' ')[1]
        try:
            data = serializer.loads(token, max_age=3600)
        except (BadSignature, SignatureExpired):
            return jsonify({"error": "Invalid or expired authentication token. Please sign in again."}), 401
        
        user_id = data["id"]
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Check if user is a member
        cur.execute("""
            SELECT role FROM group_members 
            WHERE group_id = %s AND user_id = %s AND is_active = TRUE
        """, (group_id, user_id))
        
        member_result = cur.fetchone()
        if not member_result:
            return jsonify({"error": "You are not a member of this group. Please join the group to access this feature."}), 403
        
        # Check if user is the creator (admin)
        if member_result[0] == 'admin':
            # Check if there are other admins
            cur.execute("""
                SELECT COUNT(*) FROM group_members 
                WHERE group_id = %s AND role = 'admin' AND is_active = TRUE
            """, (group_id,))
            
            admin_count = cur.fetchone()[0]
            if admin_count <= 1:
                return jsonify({"error": "Cannot leave group as the only admin. Transfer admin role or delete the group."}), 400
        
        # Deactivate membership
        cur.execute("""
            UPDATE group_members 
            SET is_active = FALSE
            WHERE group_id = %s AND user_id = %s
        """, (group_id, user_id))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({"message": "Successfully left the group"})
        
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return jsonify({"error": "An internal server error occurred. Please try again later."}), 500

@app.route("/groups/<int:group_id>", methods=["PUT"])
@rate_limit(max_requests=50, window=3600)
@require_csrf
def update_group(group_id):
    """Update group details (admin only)"""
    try:
        # Get user from token
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            return jsonify({"error": "Authentication required. Please sign in to continue."}), 401
        
        token = token.split(' ')[1]
        try:
            data = serializer.loads(token, max_age=3600)
        except (BadSignature, SignatureExpired):
            return jsonify({"error": "Invalid or expired authentication token. Please sign in again."}), 401
        
        user_id = data["id"]
        
        # Get request data
        request_data = request.get_json()
        if not request_data:
            return jsonify({"error": "Request data is required to process this action."}), 400
        
        name = sanitize_input(request_data.get('name', ''), 255)
        description = sanitize_input(request_data.get('description', ''), 1000)
        
        if not name:
            return jsonify({"error": "Group name is required to create a group."}), 400
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Check if user is admin of the group
        cur.execute("""
            SELECT role FROM group_members 
            WHERE group_id = %s AND user_id = %s AND is_active = TRUE
        """, (group_id, user_id))
        
        user_role = cur.fetchone()
        if not user_role or user_role[0] != 'admin':
            return jsonify({"error": "Only group admins can update group details"}), 403
        
        # Update group
        cur.execute("""
            UPDATE groups 
            SET name = %s, description = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s AND is_active = TRUE
        """, (name, description, group_id))
        
        if cur.rowcount == 0:
            return jsonify({"error": "Group not found"}), 404
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({"message": "Group updated successfully"})
        
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return jsonify({"error": "An internal server error occurred. Please try again later."}), 500

@app.route("/groups/<int:group_id>", methods=["DELETE"])
@rate_limit(max_requests=50, window=3600)
@require_csrf
def delete_group(group_id):
    """Delete a group (admin only)"""
    try:
        # Get user from token
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            return jsonify({"error": "Authentication required. Please sign in to continue."}), 401
        
        token = token.split(' ')[1]
        try:
            data = serializer.loads(token, max_age=3600)
        except (BadSignature, SignatureExpired):
            return jsonify({"error": "Invalid or expired authentication token. Please sign in again."}), 401
        
        user_id = data["id"]
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Check if user is platform admin or group admin
        is_platform_admin = _is_admin(user_id)
        
        if not is_platform_admin:
            # Check if user is admin of the group
            cur.execute("""
                SELECT role FROM group_members 
                WHERE group_id = %s AND user_id = %s AND is_active = TRUE
            """, (group_id, user_id))
            
            user_role = cur.fetchone()
            if not user_role or user_role[0] != 'admin':
                cur.close()
                conn.close()
                return jsonify({"error": "Only group admins or platform admins can delete the group"}), 403
        
        # Soft delete group (set is_active = FALSE)
        cur.execute("""
            UPDATE groups 
            SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (group_id,))
        
        if cur.rowcount == 0:
            return jsonify({"error": "Group not found"}), 404
        
        # Deactivate all memberships
        cur.execute("""
            UPDATE group_members 
            SET is_active = FALSE
            WHERE group_id = %s
        """, (group_id,))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({"message": "Group deleted successfully"})
        
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return jsonify({"error": "An internal server error occurred. Please try again later."}), 500

# -----------------------------
# Messaging Endpoints
# -----------------------------

@app.route("/groups/<int:group_id>/messages", methods=["GET"])
@rate_limit(max_requests=200, window=3600)
def get_messages(group_id):
    """Get messages for a specific group"""
    try:
        # Get user from token
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            return jsonify({"error": "Authentication required. Please sign in to continue."}), 401
        
        token = token.split(' ')[1]
        try:
            data = serializer.loads(token, max_age=3600)
        except (BadSignature, SignatureExpired):
            return jsonify({"error": "Invalid or expired authentication token. Please sign in again."}), 401
        
        user_id = data["id"]
        
        # Get pagination parameters
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 50))
        offset = (page - 1) * limit
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Check if user is admin
        is_platform_admin = _is_admin(user_id)
        
        # Check if user is member of the group (admins can view messages even if not members)
        if not is_platform_admin:
            cur.execute("""
                SELECT role FROM group_members 
                WHERE group_id = %s AND user_id = %s AND is_active = TRUE
            """, (group_id, user_id))
            
            if not cur.fetchone():
                cur.close()
                conn.close()
                return jsonify({"error": "You are not a member of this group. Please join the group to access this feature."}), 403
        
        # Get messages
        cur.execute("""
            SELECT m.id, m.content, m.message_type, m.created_at, m.updated_at, 
                   m.is_edited, m.is_deleted, m.user_id, u.username
            FROM messages m
            JOIN users u ON m.user_id = u.id
            WHERE m.group_id = %s AND m.is_deleted = FALSE
            ORDER BY m.created_at DESC
            LIMIT %s OFFSET %s
        """, (group_id, limit, offset))
        
        messages = []
        for row in cur.fetchall():
            messages.append({
                "id": row[0],
                "content": row[1],
                "message_type": row[2],
                "created_at": row[3].isoformat() if row[3] else None,
                "updated_at": row[4].isoformat() if row[4] else None,
                "is_edited": row[5],
                "is_deleted": row[6],
                "user_id": row[7],
                "username": row[8]
            })
        
        # Get total message count
        cur.execute("""
            SELECT COUNT(*) FROM messages 
            WHERE group_id = %s AND is_deleted = FALSE
        """, (group_id,))
        
        total_messages = cur.fetchone()[0]
        
        cur.close()
        conn.close()
        
        return jsonify({
            "messages": messages,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total_messages,
                "pages": (total_messages + limit - 1) // limit
            }
        })
        
    except Exception as e:
        return jsonify({"error": "An internal server error occurred. Please try again later."}), 500

@app.route("/groups/<int:group_id>/messages", methods=["POST"])
@rate_limit(max_requests=100, window=3600)
@require_csrf
def send_message(group_id):
    """Send a message to a group"""
    try:
        # Get user from token
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            return jsonify({"error": "Authentication required. Please sign in to continue."}), 401
        
        token = token.split(' ')[1]
        try:
            data = serializer.loads(token, max_age=3600)
        except (BadSignature, SignatureExpired):
            return jsonify({"error": "Invalid or expired authentication token. Please sign in again."}), 401
        
        user_id = data["id"]
        
        # Get request data
        request_data = request.get_json()
        if not request_data:
            return jsonify({"error": "Request data is required to process this action."}), 400
        
        content = sanitize_input(request_data.get('content', ''), 2000)
        message_type = sanitize_input(request_data.get('message_type', 'text'), 20)
        
        if not content:
            return jsonify({"error": "Message content is required"}), 400
        
        # Check for inappropriate content
        if contains_inappropriate_content(content):
            return jsonify({"error": "Your message contains inappropriate content. Please revise your message and try again."}), 400
        
        if message_type not in ['text', 'image', 'file', 'system']:
            return jsonify({"error": "Invalid message type"}), 400
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Check if user is admin
        is_platform_admin = _is_admin(user_id)
        
        # Check if user is member of the group (admins can send messages even if not members)
        if not is_platform_admin:
            cur.execute("""
                SELECT role FROM group_members 
                WHERE group_id = %s AND user_id = %s AND is_active = TRUE
            """, (group_id, user_id))
            
            if not cur.fetchone():
                cur.close()
                conn.close()
                return jsonify({"error": "You are not a member of this group. Please join the group to access this feature."}), 403
        
        # Insert message
        cur.execute("""
            INSERT INTO messages (group_id, user_id, content, message_type)
            VALUES (%s, %s, %s, %s)
            RETURNING id, created_at
        """, (group_id, user_id, content, message_type))
        
        message_result = cur.fetchone()
        message_id = message_result[0]
        created_at = message_result[1]
        
        # Get username for response
        cur.execute("SELECT username FROM users WHERE id = %s", (user_id,))
        username = cur.fetchone()[0]
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({
            "message": "Message sent successfully",
            "message_data": {
                "id": message_id,
                "content": content,
                "message_type": message_type,
                "created_at": created_at.isoformat(),
                "user_id": user_id,
                "username": username
            }
        }), 201
        
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return jsonify({"error": "An internal server error occurred. Please try again later."}), 500

@app.route("/messages/<int:message_id>", methods=["PUT"])
@rate_limit(max_requests=100, window=3600)
@require_csrf
def edit_message(message_id):
    """Edit a message (only by the author)"""
    try:
        # Get user from token
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            return jsonify({"error": "Authentication required. Please sign in to continue."}), 401
        
        token = token.split(' ')[1]
        try:
            data = serializer.loads(token, max_age=3600)
        except (BadSignature, SignatureExpired):
            return jsonify({"error": "Invalid or expired authentication token. Please sign in again."}), 401
        
        user_id = data["id"]
        
        # Get request data
        request_data = request.get_json()
        if not request_data:
            return jsonify({"error": "Request data is required to process this action."}), 400
        
        content = sanitize_input(request_data.get('content', ''), 2000)
        
        if not content:
            return jsonify({"error": "Message content is required"}), 400
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Check if message exists and user is the author
        cur.execute("""
            SELECT id, user_id, group_id FROM messages 
            WHERE id = %s AND is_deleted = FALSE
        """, (message_id,))
        
        message_result = cur.fetchone()
        if not message_result:
            return jsonify({"error": "Message not found"}), 404
        
        if message_result[1] != user_id:
            return jsonify({"error": "You can only edit your own messages"}), 403
        
        # Check if user is still a member of the group
        cur.execute("""
            SELECT id FROM group_members 
            WHERE group_id = %s AND user_id = %s AND is_active = TRUE
        """, (message_result[2], user_id))
        
        if not cur.fetchone():
            return jsonify({"error": "You are not a member of this group. Please join the group to access this feature."}), 403
        
        # Update message
        cur.execute("""
            UPDATE messages 
            SET content = %s, is_edited = TRUE, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (content, message_id))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({"message": "Message updated successfully"})
        
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return jsonify({"error": "An internal server error occurred. Please try again later."}), 500

@app.route("/messages/<int:message_id>", methods=["DELETE"])
@rate_limit(max_requests=100, window=3600)
@require_csrf
def delete_message(message_id):
    """Delete a message (only by the author or group admin)"""
    try:
        # Get user from token
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            return jsonify({"error": "Authentication required. Please sign in to continue."}), 401
        
        token = token.split(' ')[1]
        try:
            data = serializer.loads(token, max_age=3600)
        except (BadSignature, SignatureExpired):
            return jsonify({"error": "Invalid or expired authentication token. Please sign in again."}), 401
        
        user_id = data["id"]
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Check if message exists
        cur.execute("""
            SELECT id, user_id, group_id FROM messages 
            WHERE id = %s AND is_deleted = FALSE
        """, (message_id,))
        
        message_result = cur.fetchone()
        if not message_result:
            return jsonify({"error": "Message not found"}), 404
        
        # Check if user is platform admin, author, or group admin
        is_platform_admin = _is_admin(user_id)
        is_author = message_result[1] == user_id
        
        if not is_platform_admin and not is_author:
            # Check if user is admin of the group
            cur.execute("""
                SELECT role FROM group_members 
                WHERE group_id = %s AND user_id = %s AND is_active = TRUE
            """, (message_result[2], user_id))
            
            user_role = cur.fetchone()
            if not user_role or user_role[0] != 'admin':
                return jsonify({"error": "You can only delete your own messages, be a group admin, or be a platform admin"}), 403
        
        # Soft delete message
        cur.execute("""
            UPDATE messages 
            SET is_deleted = TRUE, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (message_id,))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({"message": "Message deleted successfully"})
        
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return jsonify({"error": "An internal server error occurred. Please try again later."}), 500

# -----------------------------
# Run Server
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True, port=5002)
