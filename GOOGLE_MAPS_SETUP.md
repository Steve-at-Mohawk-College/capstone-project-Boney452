# Google Maps API Setup Guide

## Overview
This guide will help you set up Google Maps API integration for searching and adding restaurants to your Flavor Quest database.

## Step 1: Get Google Maps API Key

### 1. Go to Google Cloud Console
- Visit: https://console.cloud.google.com/
- Sign in with your Google account

### 2. Create a New Project (or select existing)
- Click "Select a project" → "New Project"
- Name: "Flavor Quest"
- Click "Create"

### 3. Enable Required APIs
- Go to "APIs & Services" → "Library"
- Search and enable these APIs:
  - **Places API**
  - **Maps JavaScript API** (for frontend)
  - **Geocoding API** (optional)

### 4. Create API Key
- Go to "APIs & Services" → "Credentials"
- Click "Create Credentials" → "API Key"
- Copy the API key

### 5. Restrict API Key (Recommended)
- Click on your API key
- Under "Application restrictions":
  - Select "HTTP referrers"
  - Add your domain (e.g., `localhost:5002`, `yourdomain.com`)
- Under "API restrictions":
  - Select "Restrict key"
  - Choose: Places API, Maps JavaScript API, Geocoding API

## Step 2: Set Up Environment Variables

### Option 1: Environment Variable
```bash
export GOOGLE_MAPS_API_KEY="your_api_key_here"
```

### Option 2: Create .env file
Create a `.env` file in your backend directory:
```
GOOGLE_MAPS_API_KEY=your_api_key_here
```

### Option 3: Direct in Code (Not Recommended for Production)
Update the `GOOGLE_MAPS_API_KEY` in `app.py`:
```python
GOOGLE_MAPS_API_KEY = "your_actual_api_key_here"
```

## Step 3: Test the Integration

### 1. Start the Backend Server
```bash
cd backend
python3 app.py
```

### 2. Test Google Search
```bash
curl -X POST http://localhost:5002/google-search \
  -H "Content-Type: application/json" \
  -d '{"query": "Italian restaurants in New York"}'
```

### 3. Test Adding a Restaurant
```bash
# First, get a place_id from the search results
curl -X POST http://localhost:5002/add-google-place \
  -H "Content-Type: application/json" \
  -d '{"place_id": "ChIJN1t_tDeuEmsRUsoyG83frY4"}'
```

## API Endpoints

### 1. Search Google Places
**POST** `/google-search`

**Request Body:**
```json
{
  "query": "Italian restaurants in New York",
  "location": "40.7128,-74.0060",  // Optional: lat,lng
  "radius": 5000  // Optional: radius in meters
}
```

**Response:**
```json
{
  "places": [
    {
      "place_id": "ChIJN1t_tDeuEmsRUsoyG83frY4",
      "name": "Mario's Italian Bistro",
      "formatted_address": "123 Main St, New York, NY 10001",
      "rating": 4.5,
      "price_level": 2,
      "types": ["restaurant", "food", "establishment"],
      "geometry": {
        "location": {
          "lat": 40.7128,
          "lng": -74.0060
        }
      },
      "photos": [...]
    }
  ],
  "count": 1,
  "status": "OK"
}
```

### 2. Add Google Place to Database
**POST** `/add-google-place`

**Request Body:**
```json
{
  "place_id": "ChIJN1t_tDeuEmsRUsoyG83frY4"
}
```

**Response:**
```json
{
  "message": "Restaurant added successfully",
  "restaurant": {
    "ResturantsId": 1,
    "Name": "Mario's Italian Bistro",
    "Cuisine Type": "Italian",
    "Location": "123 Main St, New York, NY 10001",
    "GoogleApiLinks": "https://www.google.com/maps/place/?q=place_id:ChIJN1t_tDeuEmsRUsoyG83frY4",
    "CreatedAt": "2024-01-01T00:00:00"
  }
}
```

## Features

### 🔍 Smart Search
- Search by restaurant name, cuisine, or location
- Location-based search with radius
- Automatic cuisine type detection

### 🍽️ Cuisine Type Detection
The system automatically detects cuisine types from Google Places data:
- Italian, Chinese, Mexican, Indian
- Japanese, American, Thai, French
- Korean, Mediterranean, and more

### 🗺️ Google Maps Integration
- Direct Google Maps links for each restaurant
- Location coordinates for mapping
- Address validation

### 🚫 Duplicate Prevention
- Checks for existing restaurants before adding
- Prevents duplicate entries in database

## Usage Examples

### Search for Italian Restaurants
```bash
curl -X POST http://localhost:5002/google-search \
  -H "Content-Type: application/json" \
  -d '{"query": "Italian restaurants", "location": "40.7128,-74.0060", "radius": 2000}'
```

### Search by Location
```bash
curl -X POST http://localhost:5002/google-search \
  -H "Content-Type: application/json" \
  -d '{"query": "restaurants near Times Square"}'
```

### Add Multiple Restaurants
```bash
# Search first
curl -X POST http://localhost:5002/google-search \
  -H "Content-Type: application/json" \
  -d '{"query": "pizza restaurants in Manhattan"}'

# Then add each place_id from the results
curl -X POST http://localhost:5002/add-google-place \
  -H "Content-Type: application/json" \
  -d '{"place_id": "place_id_from_search_results"}'
```

## Troubleshooting

### Common Issues

1. **"Google Places API error: REQUEST_DENIED"**
   - Check if API key is correct
   - Verify Places API is enabled
   - Check API key restrictions

2. **"Google Places API error: OVER_QUERY_LIMIT"**
   - You've exceeded the API quota
   - Check your billing settings
   - Consider upgrading your plan

3. **"Google Places API request failed"**
   - Check internet connection
   - Verify API key is set correctly
   - Check if the API is enabled

### API Quotas
- **Places API Text Search**: 1,000 requests per day (free tier)
- **Places API Details**: 1,000 requests per day (free tier)
- **Upgrade to paid plan for higher limits**

## Next Steps

1. **Set up your Google Maps API key**
2. **Test the search functionality**
3. **Add restaurants to your database**
4. **Integrate with your frontend**
5. **Consider implementing batch import for multiple restaurants**

Your Flavor Quest app now has powerful Google Maps integration for restaurant discovery! 🎉
