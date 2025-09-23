from flask import Flask
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route("/")
def home():
    return {"message": "Flavor Quest API running"}

@app.route("/restaurants")
def get_restaurants():
    # Sample restaurant data - replace with actual database query later
    restaurants = [
        {
            "id": 1,
            "name": "Mario's Italian Bistro",
            "cuisine": "Italian",
            "rating": 4.5,
            "location": "Downtown"
        },
        {
            "id": 2,
            "name": "Sakura Sushi",
            "cuisine": "Japanese",
            "rating": 4.8,
            "location": "Midtown"
        },
        {
            "id": 3,
            "name": "Taco Fiesta",
            "cuisine": "Mexican",
            "rating": 4.2,
            "location": "Westside"
        }
    ]
    return {"restaurants": restaurants}

if __name__ == "__main__":
    app.run(debug=True, port=5002)
