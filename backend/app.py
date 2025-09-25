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
conn = psycopg2.connect(
    dbname="flavorquest",
    user="flavoruser",
    password="securepass",
    host="localhost",
    port="5432"
)
cur = conn.cursor()

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
        cur.execute("""
            SELECT r.id, r.name, r.cuisine_type, r.location, r.google_api_links, r.created_at
            FROM restaurants r
            WHERE r.is_active = TRUE
            ORDER BY r.created_at DESC
        """)
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
        
        return jsonify({"restaurants": restaurant_list, "count": len(restaurant_list)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/restaurants/<int:restaurant_id>")
def get_restaurant(restaurant_id):
    try:
        # Get restaurant details
        cur.execute("""
            SELECT r.id, r.name, r.cuisine_type, r.location, r.google_api_links, r.created_at
            FROM restaurants r
            WHERE r.id = %s AND r.is_active = TRUE
        """, (restaurant_id,))
        restaurant = cur.fetchone()
        
        if not restaurant:
            return jsonify({"error": "Restaurant not found"}), 404
        
        return jsonify({
            "restaurant": {
                "ResturantsId": restaurant[0],
                "Name": restaurant[1],
                "Cuisine Type": restaurant[2],
                "Location": restaurant[3],
                "GoogleApiLinks": restaurant[4],
                "CreatedAt": restaurant[5].isoformat() if restaurant[5] else None
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
        cur.execute("""
            INSERT INTO restaurants (name, cuisine_type, location, google_api_links, created_at, is_active)
            VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP, TRUE)
            RETURNING id
        """, (name, cuisine_type, location, google_api_links))
        
        restaurant_id = cur.fetchone()[0]
        conn.commit()
        
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
        conn.rollback()
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
        hashed = ph.hash(password)
        cur.execute(
            "INSERT INTO users (username, email, password_hash, created_at) VALUES (%s, %s, %s, CURRENT_TIMESTAMP)",
            (username, email, hashed)
        )
        conn.commit()
        return jsonify({"message": "User registered successfully!"}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 400

# --- Login ---
@app.route("/login", methods=["POST"])
def login():
    data = request.json
    email = data.get("email")
    password = data.get("password")

    cur.execute("SELECT id, username, password_hash FROM users WHERE email = %s", (email,))
    user = cur.fetchone()

    if not user:
        return jsonify({"error": "User not found"}), 404

    try:
        ph.verify(user[2], password)
        token = serializer.dumps({"id": user[0], "username": user[1]})
        return jsonify({"message": "Login successful", "token": token, "user": {"UserId": user[0], "UserName": user[1], "UserEmail": email}}), 200
    except Exception:
        return jsonify({"error": "Invalid password"}), 401

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
    
    # Get full user details
    cur.execute("SELECT id, username, email, created_at FROM users WHERE id = %s", (data["id"],))
    user = cur.fetchone()
    
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


# --- Search ---
@app.route("/search")
def search_restaurants():
    query = request.args.get("q", "")
    cuisine_type = request.args.get("cuisine_type", "")
    location = request.args.get("location", "")
    
    try:
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
        
        return jsonify({"restaurants": restaurant_list, "count": len(restaurant_list)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- Google Places API Search ---
@app.route("/google-search", methods=["POST"])
def search_google_places():
    # Check API quota first
    quota_ok, quota_error = check_api_quota()
    if not quota_ok:
        return jsonify({"error": quota_error}), 429
    
    data = request.json
    query = data.get("query", "")
    location = data.get("location", "")
    radius = data.get("radius", 5000)  # Default 5km radius
    
    if not query:
        return jsonify({"error": "Query is required"}), 400
    
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
        
        # Format the results
        formatted_places = []
        for place in places:
            formatted_places.append({
                "place_id": place.get("place_id"),
                "name": place.get("name"),
                "formatted_address": place.get("formatted_address"),
                "rating": place.get("rating"),
                "price_level": place.get("price_level"),
                "types": place.get("types", []),
                "geometry": place.get("geometry"),
                "photos": place.get("photos", [])
            })
        
        return jsonify({
            "places": formatted_places,
            "count": len(formatted_places),
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
    place_id = data.get("place_id")
    
    if not place_id:
        return jsonify({"error": "Place ID is required"}), 400
    
    try:
        # Get detailed information about the place
        details_url = f"{GOOGLE_PLACES_API_URL}/details/json"
        params = {
            "place_id": place_id,
            "key": GOOGLE_MAPS_API_KEY,
            "fields": "name,formatted_address,types,rating,price_level,geometry,website,formatted_phone_number"
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
        
        return jsonify({
            "message": "Restaurant added successfully",
            "restaurant": {
                "ResturantsId": restaurant_id,
                "Name": name,
                "Cuisine Type": cuisine_type,
                "Location": address,
                "GoogleApiLinks": google_maps_link,
                "CreatedAt": "2024-01-01T00:00:00"  # Will be set by database
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
        conn.rollback()
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
    
    if len(place_ids) > 10:
        return jsonify({"error": "Maximum 10 restaurants per batch"}), 400
    
    # Check if we have enough quota
    quota_ok, quota_error = check_api_quota()
    if not quota_ok:
        return jsonify({"error": quota_error}), 429
    
    if usage["total_requests"] + len(place_ids) > MAX_REQUESTS:
        return jsonify({"error": f"Not enough quota. Need {len(place_ids)} requests, have {MAX_REQUESTS - usage['total_requests']} remaining"}), 429
    
    results = []
    errors = []
    
    for place_id in place_ids:
        try:
            # Get detailed information about the place
            details_url = f"{GOOGLE_PLACES_API_URL}/details/json"
            params = {
                "place_id": place_id,
                "key": GOOGLE_MAPS_API_KEY,
                "fields": "name,formatted_address,types,rating,price_level,geometry,website,formatted_phone_number"
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
        "message": f"Batch processing completed. {len(results)} restaurants added, {len(errors)} errors.",
        "restaurants": results,
        "errors": errors,
        "api_usage": {
            "total_requests": usage["total_requests"],
            "remaining_requests": MAX_REQUESTS - usage["total_requests"],
            "daily_requests": usage["daily_requests"]
        }
    }), 201

# --- Database Viewer (for development) ---
@app.route("/users")
def get_users():
    try:
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
        return jsonify({"users": user_list, "count": len(user_list)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# -----------------------------
# Run Server
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True, port=5002)
