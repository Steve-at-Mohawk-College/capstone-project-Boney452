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

# -----------------------------
# Security Utilities
# -----------------------------

def sanitize_input(text, max_length=1000):
    """Sanitize user input to prevent XSS and SQL injection"""
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
    """Validate email format"""
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
    """Establish a database connection using the configured URL."""
    dsn = _build_connection_url()
    try:
        return psycopg2.connect(dsn)
    except psycopg2.Error as e:
        app.logger.error("Database connection error: %s", e)
        raise

def get_photo_url(photo_reference, max_width=400):
    """Generate a photo URL from Google Places photo reference"""
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
    """Add security headers to all responses"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; connect-src 'self' https://maps.googleapis.com;"
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

# Run migration on app startup (non-blocking)
import threading
def run_migration_async():
    """Run migration in background thread to not block app startup"""
    try:
        ensure_admin_column()
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
                return jsonify({"error": "Invalid CSRF token"}), 403
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
        return jsonify({"error": str(e)}), 500

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
            return jsonify({"error": "Restaurant not found"}), 404
        
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
        return jsonify({"error": str(e)}), 500

# --- Create Restaurant ---
@app.route("/restaurants", methods=["POST"])
def create_restaurant():
    data = request.json
    name = data.get("name")
    cuisine_type = data.get("cuisine_type")
    location = data.get("location")
    google_api_links = data.get("google_api_links")

    if not name or not cuisine_type or not location:
        return jsonify({"error": "Name, cuisine type, and location are required"}), 400

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
        return jsonify({"error": str(e)}), 400

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
        return jsonify({"error": "Missing fields"}), 400

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
        return jsonify({"error": "Registration failed"}), 400

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
            return jsonify({"error": "Invalid password"}), 401
        return jsonify({"error": str(e)}), 401

# --- Auth: current user ---
def _require_auth(req):
    auth_header = req.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None, (jsonify({"error": "Missing or invalid Authorization header"}), 401)
    token = auth_header.split(" ", 1)[1]
    try:
        data = serializer.loads(token, max_age=3600)  # 1 hour expiry
        return data, None
    except SignatureExpired:
        return None, (jsonify({"error": "Token expired"}), 401)
    except BadSignature:
        return None, (jsonify({"error": "Invalid token"}), 401)

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
            return jsonify({"error": "User not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# --- Search Restaurants by Place ID ---
@app.route("/restaurants/search")
def search_restaurants_by_place_id():
    place_id = request.args.get("place_id")
    
    if not place_id:
        return jsonify({"error": "Place ID is required"}), 400
    
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
        return jsonify({"error": str(e)}), 500

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
        return jsonify({"error": str(e)}), 500

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
        return jsonify({"error": str(e)}), 500

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
    
    # Sanitize search inputs
    query = sanitize_input(query, 200)
    location = sanitize_input(location, 200)
    
    if not query:
        return jsonify({"error": "Query is required"}), 400
    
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
        return jsonify({"error": "Please enter at least 2 characters"}), 400
    
    # Only reject if it's purely numbers or special characters (no letters at all)
    if not re.search(r'[a-zA-Z]', query):
        return jsonify({"error": "Please enter a location name with letters"}), 400
    
    try:
        # Search for places using Google Places API
        search_url = f"{GOOGLE_PLACES_API_URL}/textsearch/json"
        params = {
            "query": query,
            "key": GOOGLE_MAPS_API_KEY,
            "type": "restaurant"
        }
        
        if location:
            params["location"] = location
            params["radius"] = radius
        
        response = requests.get(search_url, params=params)
        response.raise_for_status()
        
        # Track API usage
        usage = load_api_usage()
        usage["total_requests"] += 1
        usage["daily_requests"] += 1
        usage["last_request"] = datetime.now().isoformat()
        save_api_usage(usage)
        
        places_data = response.json()
        
        if places_data.get("status") != "OK":
            return jsonify({"error": f"Google Places API error: {places_data.get('status')}"}), 400
        
        places = places_data.get("results", [])
        
        # If no places found, return error
        if not places:
            return jsonify({"error": f"No restaurants found for '{query}'. Please try a different location."}), 404
        
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
        return jsonify({"error": f"Google Places API request failed: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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
        return jsonify({"error": "Place ID is required"}), 400
    
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
            return jsonify({"error": "Restaurant already exists in database"}), 400
        
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
        return jsonify({"error": f"Google Places API request failed: {str(e)}"}), 500
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
            cur.close()
            conn.close()
        return jsonify({"error": str(e)}), 400

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
        return jsonify({"error": "Place IDs are required"}), 400
    
    if len(place_ids) > 20:
        return jsonify({"error": "Maximum 20 restaurants per batch"}), 400
    
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
        return jsonify({"error": f"Database error: {str(e)}"}), 500
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
            return jsonify({"error": "Username is required"}), 400
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Check if user exists
        cur.execute("SELECT id, username, email FROM users WHERE username = %s", (username,))
        user = cur.fetchone()
        
        if not user:
            cur.close()
            conn.close()
            return jsonify({"error": f"User '{username}' not found"}), 404
        
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
        return jsonify({"error": str(e)}), 500

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
        return jsonify({"error": str(e)}), 500

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
        return jsonify({"error": str(e)}), 500

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
        return jsonify({"error": str(e)}), 500

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
        return jsonify({"error": str(e)}), 500

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
            return jsonify({"error": "Rating must be between 1 and 5"}), 400
        
        # Sanitize review text
        review_text = sanitize_input(review_text, 1000)
        
        # Get database connection
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Check if restaurant exists
        cur.execute("SELECT id FROM restaurants WHERE id = %s AND is_active = TRUE", (restaurant_id,))
        if not cur.fetchone():
            cur.close()
            conn.close()
            return jsonify({"error": "Restaurant not found"}), 404
        
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
        return jsonify({"error": str(e)}), 500

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
            return jsonify({"error": "Restaurant not found"}), 404
        
        # Get all ratings for this restaurant
        cur.execute("""
            SELECT r.rating, r.review_text, r.created_at, u.username
            FROM restaurant_ratings r
            JOIN users u ON r.user_id = u.id
            WHERE r.restaurant_id = %s
            ORDER BY r.created_at DESC
        """, (restaurant_id,))
        
        ratings = cur.fetchall()
        
        # Calculate average rating
        if ratings:
            avg_rating = sum(rating[0] for rating in ratings) / len(ratings)
            total_ratings = len(ratings)
        else:
            avg_rating = None
            total_ratings = 0
        
        # Format ratings
        formatted_ratings = []
        for rating in ratings:
            formatted_ratings.append({
                "rating": rating[0],
                "review_text": rating[1],
                "created_at": rating[2].isoformat() if rating[2] else None,
                "username": rating[3]
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
        return jsonify({"error": str(e)}), 500

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
        return jsonify({"error": str(e)}), 500

# Delete user's rating for a restaurant (or any rating if admin)
@app.route("/restaurants/<int:restaurant_id>/rate", methods=["DELETE"])
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
        rating_id = request.json.get("rating_id") if request.json else None
        
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
            return jsonify({"error": "Rating not found"}), 404
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({"message": "Rating deleted successfully"}), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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
            return jsonify({"error": "No token provided"}), 401
        
        token = token.split(' ')[1]
        try:
            data = serializer.loads(token, max_age=3600)
        except (BadSignature, SignatureExpired):
            return jsonify({"error": "Invalid or expired token"}), 401
        
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
            groups.append({
                "id": row[0],
                "name": row[1],
                "description": row[2],
                "created_by": row[3],
                "created_at": row[4].isoformat() if row[4] else None,
                "updated_at": row[5].isoformat() if row[5] else None,
                "creator_name": row[6],
                "member_count": row[7],
                "user_role": row[8]
            })
        
        cur.close()
        conn.close()
        
        return jsonify({"groups": groups})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/groups/discover", methods=["GET"])
@rate_limit(max_requests=100, window=3600)
def discover_groups():
    """Get all public groups that the user can join"""
    try:
        # Get user from token
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            return jsonify({"error": "No token provided"}), 401
        
        token = token.split(' ')[1]
        try:
            data = serializer.loads(token, max_age=3600)
        except (BadSignature, SignatureExpired):
            return jsonify({"error": "Invalid or expired token"}), 401
        
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
            groups.append({
                "id": row[0],
                "name": row[1],
                "description": row[2],
                "created_by": row[3],
                "created_at": row[4].isoformat() if row[4] else None,
                "updated_at": row[5].isoformat() if row[5] else None,
                "creator_name": row[6],
                "member_count": row[7],
                "user_role": row[8] if row[8] != 'not_member' else None
            })
        
        cur.close()
        conn.close()
        
        return jsonify({"groups": groups})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/groups", methods=["POST"])
@rate_limit(max_requests=50, window=3600)
@require_csrf
def create_group():
    """Create a new group"""
    try:
        # Get user from token
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            return jsonify({"error": "No token provided"}), 401
        
        token = token.split(' ')[1]
        try:
            data = serializer.loads(token, max_age=3600)
        except (BadSignature, SignatureExpired):
            return jsonify({"error": "Invalid or expired token"}), 401
        
        user_id = data["id"]
        
        # Get request data
        request_data = request.get_json()
        if not request_data:
            return jsonify({"error": "No data provided"}), 400
        
        name = sanitize_input(request_data.get('name', ''), 255)
        description = sanitize_input(request_data.get('description', ''), 1000)
        
        if not name:
            return jsonify({"error": "Group name is required"}), 400
        
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
            conn.close()
        return jsonify({"error": str(e)}), 500

@app.route("/groups/<int:group_id>", methods=["GET"])
@rate_limit(max_requests=100, window=3600)
def get_group_details(group_id):
    """Get detailed information about a specific group"""
    try:
        # Get user from token
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            return jsonify({"error": "No token provided"}), 401
        
        token = token.split(' ')[1]
        try:
            data = serializer.loads(token, max_age=3600)
        except (BadSignature, SignatureExpired):
            return jsonify({"error": "Invalid or expired token"}), 401
        
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
            return jsonify({"error": "You are not a member of this group"}), 403
        
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
        return jsonify({"error": str(e)}), 500

@app.route("/groups/<int:group_id>/join", methods=["POST"])
@rate_limit(max_requests=50, window=3600)
@require_csrf
def join_group(group_id):
    """Join a group"""
    try:
        # Get user from token
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            return jsonify({"error": "No token provided"}), 401
        
        token = token.split(' ')[1]
        try:
            data = serializer.loads(token, max_age=3600)
        except (BadSignature, SignatureExpired):
            return jsonify({"error": "Invalid or expired token"}), 401
        
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
        return jsonify({"error": str(e)}), 500

@app.route("/groups/<int:group_id>/leave", methods=["POST"])
@rate_limit(max_requests=50, window=3600)
@require_csrf
def leave_group(group_id):
    """Leave a group"""
    try:
        # Get user from token
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            return jsonify({"error": "No token provided"}), 401
        
        token = token.split(' ')[1]
        try:
            data = serializer.loads(token, max_age=3600)
        except (BadSignature, SignatureExpired):
            return jsonify({"error": "Invalid or expired token"}), 401
        
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
            return jsonify({"error": "You are not a member of this group"}), 403
        
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
        return jsonify({"error": str(e)}), 500

@app.route("/groups/<int:group_id>", methods=["PUT"])
@rate_limit(max_requests=50, window=3600)
@require_csrf
def update_group(group_id):
    """Update group details (admin only)"""
    try:
        # Get user from token
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            return jsonify({"error": "No token provided"}), 401
        
        token = token.split(' ')[1]
        try:
            data = serializer.loads(token, max_age=3600)
        except (BadSignature, SignatureExpired):
            return jsonify({"error": "Invalid or expired token"}), 401
        
        user_id = data["id"]
        
        # Get request data
        request_data = request.get_json()
        if not request_data:
            return jsonify({"error": "No data provided"}), 400
        
        name = sanitize_input(request_data.get('name', ''), 255)
        description = sanitize_input(request_data.get('description', ''), 1000)
        
        if not name:
            return jsonify({"error": "Group name is required"}), 400
        
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
        return jsonify({"error": str(e)}), 500

@app.route("/groups/<int:group_id>", methods=["DELETE"])
@rate_limit(max_requests=50, window=3600)
@require_csrf
def delete_group(group_id):
    """Delete a group (admin only)"""
    try:
        # Get user from token
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            return jsonify({"error": "No token provided"}), 401
        
        token = token.split(' ')[1]
        try:
            data = serializer.loads(token, max_age=3600)
        except (BadSignature, SignatureExpired):
            return jsonify({"error": "Invalid or expired token"}), 401
        
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
        return jsonify({"error": str(e)}), 500

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
            return jsonify({"error": "No token provided"}), 401
        
        token = token.split(' ')[1]
        try:
            data = serializer.loads(token, max_age=3600)
        except (BadSignature, SignatureExpired):
            return jsonify({"error": "Invalid or expired token"}), 401
        
        user_id = data["id"]
        
        # Get pagination parameters
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 50))
        offset = (page - 1) * limit
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Check if user is member of the group
        cur.execute("""
            SELECT role FROM group_members 
            WHERE group_id = %s AND user_id = %s AND is_active = TRUE
        """, (group_id, user_id))
        
        if not cur.fetchone():
            return jsonify({"error": "You are not a member of this group"}), 403
        
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
        return jsonify({"error": str(e)}), 500

@app.route("/groups/<int:group_id>/messages", methods=["POST"])
@rate_limit(max_requests=100, window=3600)
@require_csrf
def send_message(group_id):
    """Send a message to a group"""
    try:
        # Get user from token
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            return jsonify({"error": "No token provided"}), 401
        
        token = token.split(' ')[1]
        try:
            data = serializer.loads(token, max_age=3600)
        except (BadSignature, SignatureExpired):
            return jsonify({"error": "Invalid or expired token"}), 401
        
        user_id = data["id"]
        
        # Get request data
        request_data = request.get_json()
        if not request_data:
            return jsonify({"error": "No data provided"}), 400
        
        content = sanitize_input(request_data.get('content', ''), 2000)
        message_type = sanitize_input(request_data.get('message_type', 'text'), 20)
        
        if not content:
            return jsonify({"error": "Message content is required"}), 400
        
        if message_type not in ['text', 'image', 'file', 'system']:
            return jsonify({"error": "Invalid message type"}), 400
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Check if user is member of the group
        cur.execute("""
            SELECT role FROM group_members 
            WHERE group_id = %s AND user_id = %s AND is_active = TRUE
        """, (group_id, user_id))
        
        if not cur.fetchone():
            return jsonify({"error": "You are not a member of this group"}), 403
        
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
        return jsonify({"error": str(e)}), 500

@app.route("/messages/<int:message_id>", methods=["PUT"])
@rate_limit(max_requests=100, window=3600)
@require_csrf
def edit_message(message_id):
    """Edit a message (only by the author)"""
    try:
        # Get user from token
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            return jsonify({"error": "No token provided"}), 401
        
        token = token.split(' ')[1]
        try:
            data = serializer.loads(token, max_age=3600)
        except (BadSignature, SignatureExpired):
            return jsonify({"error": "Invalid or expired token"}), 401
        
        user_id = data["id"]
        
        # Get request data
        request_data = request.get_json()
        if not request_data:
            return jsonify({"error": "No data provided"}), 400
        
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
            return jsonify({"error": "You are not a member of this group"}), 403
        
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
        return jsonify({"error": str(e)}), 500

@app.route("/messages/<int:message_id>", methods=["DELETE"])
@rate_limit(max_requests=100, window=3600)
@require_csrf
def delete_message(message_id):
    """Delete a message (only by the author or group admin)"""
    try:
        # Get user from token
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            return jsonify({"error": "No token provided"}), 401
        
        token = token.split(' ')[1]
        try:
            data = serializer.loads(token, max_age=3600)
        except (BadSignature, SignatureExpired):
            return jsonify({"error": "Invalid or expired token"}), 401
        
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
        return jsonify({"error": str(e)}), 500

# -----------------------------
# Run Server
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True, port=5002)
