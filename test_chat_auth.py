#!/usr/bin/env python3
"""
Test script for chat API with authentication
"""

import requests
import json

BASE_URL = "http://localhost:5002"

def test_chat_with_auth():
    """Test the chat API endpoints with proper authentication"""
    print("🧪 Testing Chat API with Authentication")
    print("=" * 50)
    
    # Step 1: Create a test user first
    print("\n1. Creating a test user...")
    try:
        # Get CSRF token first
        csrf_response = requests.get(f"{BASE_URL}/csrf-token")
        if csrf_response.status_code == 200:
            csrf_token = csrf_response.json().get('csrf_token')
            print(f"   ✅ CSRF token obtained")
        else:
            print(f"   ❌ CSRF token failed: {csrf_response.status_code}")
            return
        
        # Create user
        signup_data = {
            "username": "testuser2",
            "email": "test2@example.com", 
            "password": "Test123!"
        }
        headers = {
            "Content-Type": "application/json",
            "X-CSRF-Token": csrf_token
        }
        response = requests.post(f"{BASE_URL}/signup", json=signup_data, headers=headers)
        if response.status_code == 201:
            print(f"   ✅ Test user created successfully")
        elif response.status_code == 400 and "already exists" in str(response.json()):
            print(f"   ✅ Test user already exists")
        else:
            print(f"   ❌ User creation failed: {response.status_code}")
            print(f"   Response: {response.json()}")
    except Exception as e:
        print(f"   ❌ User creation error: {e}")
    
    # Step 2: Login to get a token
    print("\n2. Logging in to get authentication token...")
    login_data = {
        "email": "test2@example.com",
        "password": "Test123!"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/login", json=login_data)
        if response.status_code == 200:
            token_data = response.json()
            token = token_data.get('token')
            user_id = token_data.get('user', {}).get('id')
            print(f"   ✅ Login successful! User ID: {user_id}")
            print(f"   Token: {token[:50]}..." if token else "   No token received")
        else:
            print(f"   ❌ Login failed: {response.status_code}")
            print(f"   Response: {response.json()}")
            return
    except Exception as e:
        print(f"   ❌ Login error: {e}")
        return
    
    # Step 3: Get CSRF token for further operations
    print("\n3. Getting CSRF token for further operations...")
    try:
        response = requests.get(f"{BASE_URL}/csrf-token")
        if response.status_code == 200:
            csrf_data = response.json()
            csrf_token = csrf_data.get('csrf_token')
            print(f"   ✅ CSRF token obtained")
        else:
            print(f"   ❌ CSRF token failed: {response.status_code}")
            return
    except Exception as e:
        print(f"   ❌ CSRF token error: {e}")
        return
    
    # Step 4: Test getting groups
    print("\n4. Testing GET /groups with authentication...")
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/groups", headers=headers)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            groups_data = response.json()
            print(f"   ✅ Groups retrieved: {len(groups_data.get('groups', []))} groups")
            for group in groups_data.get('groups', []):
                print(f"      - {group.get('name')} ({group.get('member_count')} members)")
        else:
            print(f"   ❌ Error: {response.json()}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Step 5: Test creating a group
    print("\n5. Testing POST /groups (create group)...")
    try:
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-CSRF-Token": csrf_token
        }
        group_data = {
            "name": "Test Chat Group",
            "description": "A test group created by the API test script"
        }
        response = requests.post(f"{BASE_URL}/groups", json=group_data, headers=headers)
        print(f"   Status: {response.status_code}")
        if response.status_code == 201:
            group_info = response.json()
            print(f"   ✅ Group created: {group_info.get('group', {}).get('name')}")
            group_id = group_info.get('group', {}).get('id')
        else:
            print(f"   ❌ Error: {response.json()}")
            return
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return
    
    # Step 6: Test sending a message
    print("\n6. Testing POST /groups/{id}/messages (send message)...")
    try:
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-CSRF-Token": csrf_token
        }
        message_data = {
            "content": "Hello from the API test! This is a test message.",
            "message_type": "text"
        }
        response = requests.post(f"{BASE_URL}/groups/{group_id}/messages", json=message_data, headers=headers)
        print(f"   Status: {response.status_code}")
        if response.status_code == 201:
            message_info = response.json()
            print(f"   ✅ Message sent: {message_info.get('message_data', {}).get('content')[:50]}...")
        else:
            print(f"   ❌ Error: {response.json()}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Step 7: Test getting messages
    print("\n7. Testing GET /groups/{id}/messages (get messages)...")
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/groups/{group_id}/messages", headers=headers)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            messages_data = response.json()
            messages = messages_data.get('messages', [])
            print(f"   ✅ Messages retrieved: {len(messages)} messages")
            for msg in messages[:3]:  # Show first 3 messages
                print(f"      - {msg.get('username')}: {msg.get('content')[:30]}...")
        else:
            print(f"   ❌ Error: {response.json()}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print("\n🎉 Chat API authentication test completed!")
    print("\nIf all tests passed, the chat system should work properly in the frontend.")

if __name__ == "__main__":
    test_chat_with_auth()
