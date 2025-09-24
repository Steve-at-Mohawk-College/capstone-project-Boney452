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

# --- Restaurants (sample) ---
@app.route("/restaurants")
def get_restaurants():
    # Sample data for now
    restaurants = [
        {"id": 1, "name": "Mario's Italian Bistro", "cuisine": "Italian", "rating": 4.5, "location": "Downtown"},
        {"id": 2, "name": "Sakura Sushi", "cuisine": "Japanese", "rating": 4.8, "location": "Midtown"},
        {"id": 3, "name": "Taco Fiesta", "cuisine": "Mexican", "rating": 4.2, "location": "Westside"}
    ]
    return {"restaurants": restaurants}

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
            "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)",
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
        return jsonify({"message": "Login successful", "token": token}), 200
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
    return jsonify({"user": data})

# --- Database Viewer (for development) ---
@app.route("/users")
def get_users():
    try:
        cur.execute("SELECT id, username, email, created_at FROM users ORDER BY created_at DESC")
        users = cur.fetchall()
        user_list = []
        for user in users:
            user_list.append({
                "id": user[0],
                "username": user[1],
                "email": user[2],
                "created_at": user[3].isoformat() if user[3] else None
            })
        return jsonify({"users": user_list, "count": len(user_list)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# -----------------------------
# Run Server
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True, port=5002)
