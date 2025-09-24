import psycopg2
from flask import Flask, request, jsonify
from flask_cors import CORS
from argon2 import PasswordHasher
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

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
