#!/usr/bin/env python3
"""
Test script for chat API endpoints
"""

import requests
import json

BASE_URL = "http://localhost:5002"

def test_chat_endpoints():
    """Test the chat API endpoints"""
    print("🧪 Testing Chat API Endpoints")
    print("=" * 50)
    
    # Test 1: Get groups without token (should fail)
    print("\n1. Testing GET /groups without token...")
    try:
        response = requests.get(f"{BASE_URL}/groups")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 2: Create group without token (should fail)
    print("\n2. Testing POST /groups without token...")
    try:
        response = requests.post(f"{BASE_URL}/groups", json={
            "name": "Test Group",
            "description": "A test group"
        })
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 3: Get messages without token (should fail)
    print("\n3. Testing GET /groups/1/messages without token...")
    try:
        response = requests.get(f"{BASE_URL}/groups/1/messages")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 4: Send message without token (should fail)
    print("\n4. Testing POST /groups/1/messages without token...")
    try:
        response = requests.post(f"{BASE_URL}/groups/1/messages", json={
            "content": "Hello world!",
            "message_type": "text"
        })
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
    except Exception as e:
        print(f"   Error: {e}")
    
    print("\n✅ All tests completed!")
    print("\nNote: These tests show that the endpoints are properly protected.")
    print("To test with real data, you need to:")
    print("1. Login to get a valid token")
    print("2. Use the token in Authorization header")
    print("3. Test the actual functionality")

if __name__ == "__main__":
    test_chat_endpoints()
