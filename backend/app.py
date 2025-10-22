import psycopg2
from flask import Flask, request, jsonify
from flask_cors import CORS
from argon2 import PasswordHasher
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
import requests
import os
import json
from datetime import datetime

# -----------------------------
# Database Connection
# -----------------------------
def get_db_connection():
    return psycopg2.connect(
    dbname="flavorquest",
    user="flavoruser",
    password="securepass",
    host="localhost",
    port="5432"
)

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

# Password hasher
ph = PasswordHasher()

# Token serializer
serializer = URLSafeTimedSerializer("supersecret")  # change this secret in production

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

# --- Restaurants ---
@app.route("/restaurants")
def get_restaurants():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT r.id, r.name, r.cuisine_type, r.location, r.google_api_links, r.created_at,
                   COALESCE(AVG(rr.rating), 0) as avg_rating,
                   COUNT(rr.id) as total_ratings
            FROM restaurants r
            LEFT JOIN restaurant_ratings rr ON r.id = rr.restaurant_id
            WHERE r.is_active = TRUE
            GROUP BY r.id, r.name, r.cuisine_type, r.location, r.google_api_links, r.created_at
            ORDER BY r.created_at DESC
        """)
        restaurants = cur.fetchall()
        
        restaurant_list = []
        for restaurant in restaurants:
            avg_rating = float(restaurant[6]) if restaurant[6] else 0
            total_ratings = restaurant[7]
            
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
                "CreatedAt": restaurant[5].isoformat() if restaurant[5] else None,
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
            SELECT r.id, r.name, r.cuisine_type, r.location, r.google_api_links, r.created_at,
                   COALESCE(AVG(rr.rating), 0) as avg_rating,
                   COUNT(rr.id) as total_ratings
            FROM restaurants r
            LEFT JOIN restaurant_ratings rr ON r.id = rr.restaurant_id
            WHERE r.id = %s AND r.is_active = TRUE
            GROUP BY r.id, r.name, r.cuisine_type, r.location, r.google_api_links, r.created_at
        """, (restaurant_id,))
        restaurant = cur.fetchone()
        
        cur.close()
        conn.close()
        
        if not restaurant:
            return jsonify({"error": "Restaurant not found"}), 404
        
        avg_rating = float(restaurant[6]) if restaurant[6] else 0
        total_ratings = restaurant[7]
        
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
                "CreatedAt": restaurant[5].isoformat() if restaurant[5] else None,
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
def signup():
    data = request.json
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")

    if not username or not email or not password:
        return jsonify({"error": "Missing fields"}), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        hashed = ph.hash(password)
        cur.execute(
            "INSERT INTO users (username, email, password_hash, created_at) VALUES (%s, %s, %s, CURRENT_TIMESTAMP)",
            (username, email, hashed)
        )
        conn.commit()
        
        cur.close()
        conn.close()
        return jsonify({"message": "User registered successfully!"}), 201
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return jsonify({"error": str(e)}), 400

# --- Login ---
@app.route("/login", methods=["POST"])
def login():
    data = request.json
    email = data.get("email")
    password = data.get("password")

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("SELECT id, username, password_hash FROM users WHERE email = %s", (email,))
        user = cur.fetchone()

        if not user:
            cur.close()
            conn.close()
            return jsonify({"error": "User not found"}), 404

        ph.verify(user[2], password)
        token = serializer.dumps({"id": user[0], "username": user[1]})
        
        cur.close()
        conn.close()
        return jsonify({"message": "Login successful", "token": token, "user": {"UserId": user[0], "UserName": user[1], "UserEmail": email}}), 200
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


@app.route("/me")
def me():
    data, error = _require_auth(request)
    if error is not None:
        return error
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Get full user details
        cur.execute("SELECT id, username, email, created_at FROM users WHERE id = %s", (data["id"],))
        user = cur.fetchone()
        
        cur.close()
        conn.close()
        
        if user:
            return jsonify({
                "user": {
                    "UserId": user[0],
                    "UserName": user[1], 
                    "UserEmail": user[2],
                    "CreatedAt": user[3].isoformat() if user[3] else None
                }
            })
        else:
            return jsonify({"error": "User not found"}), 404
    except Exception as e:
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
@app.route("/google-search", methods=["POST"])
def search_google_places():
    # Check API quota first
    quota_ok, quota_error = check_api_quota()
    if not quota_ok:
        return jsonify({"error": quota_error}), 429
    
    data = request.json
    query = data.get("query", "").strip()
    location = data.get("location", "").strip()
    radius = data.get("radius", 5000)  # Default 5km radius
    
    if not query:
        return jsonify({"error": "Query is required"}), 400
    
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
                    "photo_url": photo_url
                }
                formatted_places.append(formatted_place)
                
                # Try to save to database
                try:
                    # Extract restaurant information
                    name = place.get("name", "")
                    address = place.get("formatted_address", "")
                    types = place.get("types", [])
                    
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
                        # Insert into database
                        cur.execute("""
                            INSERT INTO restaurants (name, cuisine_type, location, google_api_links, created_at, is_active)
                            VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP, TRUE)
                            RETURNING id
                        """, (name, cuisine_type, address, google_maps_link))
                        
                        restaurant_id = cur.fetchone()[0]
                        saved_count += 1
                        
                except Exception as e:
                    # If saving fails, continue with other restaurants
                    print(f"Failed to save restaurant {name}: {str(e)}")
                    continue
            
            # Commit all database changes
            conn.commit()
            
        finally:
            cur.close()
            conn.close()
        
        return jsonify({
            "places": formatted_places,
            "count": len(formatted_places),
            "saved_to_database": saved_count,
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
        
        # Insert into database
        cur.execute("""
            INSERT INTO restaurants (name, cuisine_type, location, google_api_links, created_at, is_active)
            VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP, TRUE)
            RETURNING id
        """, (name, cuisine_type, address, google_maps_link))
        
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
                    INSERT INTO restaurants (name, cuisine_type, location, google_api_links, created_at, is_active)
                    VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP, TRUE)
                    RETURNING id
                """, (name, cuisine_type, address, google_maps_link))
                
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

# --- Database Viewer (for development) ---
@app.route("/users")
def get_users():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("SELECT id, username, email, created_at FROM users ORDER BY created_at DESC")
        users = cur.fetchall()
        user_list = []
        for user in users:
            user_list.append({
                "UserId": user[0],
                "UserName": user[1],
                "UserEmail": user[2],
                "CreatedAt": user[3].isoformat() if user[3] else None
            })
        
        cur.close()
        conn.close()
        return jsonify({"users": user_list, "count": len(user_list)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- Restaurant Rating System ---

# Rate a restaurant
@app.route("/restaurants/<int:restaurant_id>/rate", methods=["POST"])
def rate_restaurant(restaurant_id):
    # Check authentication
    data, error = _require_auth(request)
    if error is not None:
        return error
    
    try:
        rating_data = request.json
        rating = rating_data.get("rating")
        review_text = rating_data.get("review_text", "")
        
        # Validate rating
        if not rating or not isinstance(rating, int) or rating < 1 or rating > 5:
            return jsonify({"error": "Rating must be an integer between 1 and 5"}), 400
        
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
            return jsonify({"message": "You have not rated this restaurant yet"}), 404
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Delete user's rating for a restaurant
@app.route("/restaurants/<int:restaurant_id>/rate", methods=["DELETE"])
def delete_restaurant_rating(restaurant_id):
    # Check authentication
    data, error = _require_auth(request)
    if error is not None:
        return error
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Delete user's rating
        cur.execute("""
            DELETE FROM restaurant_ratings
            WHERE restaurant_id = %s AND user_id = %s
            RETURNING id
        """, (restaurant_id, data["id"]))
        
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
# Run Server
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True, port=5002)
