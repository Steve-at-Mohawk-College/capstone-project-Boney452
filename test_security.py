#!/usr/bin/env python3
"""
Security Testing Script for Flavor Quest
Tests XSS, SQL Injection, and CSRF protections
"""

import requests
import json
import time

# Configuration
BASE_URL = "http://localhost:5002"
TEST_EMAIL = "test@example.com"
TEST_PASSWORD = "TestPassword123"

def get_csrf_token():
    """Get CSRF token from the server"""
    try:
        response = requests.get(f"{BASE_URL}/csrf-token")
        if response.status_code == 200:
            return response.json().get('csrf_token')
    except Exception as e:
        print(f"Error getting CSRF token: {e}")
    return None

def test_xss_protection():
    """Test XSS protection in various endpoints"""
    print("\n🔒 Testing XSS Protection...")
    
    xss_payloads = [
        "<script>alert('XSS')</script>",
        "<img src='x' onerror='alert(\"XSS\")'>",
        "javascript:alert('XSS')",
        "<svg onload='alert(\"XSS\")'>",
        "';alert('XSS');//"
    ]
    
    # Test search endpoint
    print("  Testing search endpoint...")
    for payload in xss_payloads:
        try:
            response = requests.post(f"{BASE_URL}/google-search", 
                json={"query": payload, "location": "test"},
                headers={"Content-Type": "application/json"})
            print(f"    Payload: {payload[:30]}... -> Status: {response.status_code}")
        except Exception as e:
            print(f"    Error testing payload: {e}")

def test_sql_injection_protection():
    """Test SQL injection protection"""
    print("\n🔒 Testing SQL Injection Protection...")
    
    sql_payloads = [
        "'; DROP TABLE restaurants; --",
        "' OR '1'='1",
        "' UNION SELECT * FROM users --",
        "admin'--",
        "' OR 1=1 --"
    ]
    
    # Test search endpoint
    print("  Testing search endpoint...")
    for payload in sql_payloads:
        try:
            response = requests.post(f"{BASE_URL}/google-search",
                json={"query": "restaurants", "location": payload},
                headers={"Content-Type": "application/json"})
            print(f"    Payload: {payload[:30]}... -> Status: {response.status_code}")
        except Exception as e:
            print(f"    Error testing payload: {e}")

def test_csrf_protection():
    """Test CSRF protection"""
    print("\n🔒 Testing CSRF Protection...")
    
    # Test without CSRF token
    print("  Testing without CSRF token...")
    try:
        response = requests.post(f"{BASE_URL}/restaurants/1/rate",
            json={"rating": 5, "review": "test review"},
            headers={"Content-Type": "application/json"})
        print(f"    No CSRF token -> Status: {response.status_code}")
        if response.status_code == 403:
            print("    ✅ CSRF protection working!")
        else:
            print("    ❌ CSRF protection may not be working")
    except Exception as e:
        print(f"    Error testing CSRF: {e}")
    
    # Test with invalid CSRF token
    print("  Testing with invalid CSRF token...")
    try:
        response = requests.post(f"{BASE_URL}/restaurants/1/rate",
            json={"rating": 5, "review": "test review"},
            headers={
                "Content-Type": "application/json",
                "X-CSRF-Token": "invalid_token"
            })
        print(f"    Invalid CSRF token -> Status: {response.status_code}")
        if response.status_code == 403:
            print("    ✅ CSRF protection working!")
        else:
            print("    ❌ CSRF protection may not be working")
    except Exception as e:
        print(f"    Error testing CSRF: {e}")

def test_input_validation():
    """Test input validation"""
    print("\n🔒 Testing Input Validation...")
    
    # Test email validation
    print("  Testing email validation...")
    invalid_emails = [
        "invalid-email",
        "test@",
        "@domain.com",
        "test@domain"
    ]
    
    for email in invalid_emails:
        try:
            response = requests.post(f"{BASE_URL}/signup",
                json={
                    "username": "testuser",
                    "email": email,
                    "password": "TestPassword123",
                    "confirm_password": "TestPassword123"
                },
                headers={"Content-Type": "application/json"})
            print(f"    Email: {email} -> Status: {response.status_code}")
        except Exception as e:
            print(f"    Error testing email: {e}")
    
    # Test password validation
    print("  Testing password validation...")
    invalid_passwords = [
        "123",  # too short, no uppercase, no lowercase
        "password",  # no numbers, no uppercase
        "PASSWORD",  # no numbers, no lowercase
        "Password"  # no numbers
    ]
    
    for password in invalid_passwords:
        try:
            response = requests.post(f"{BASE_URL}/signup",
                json={
                    "username": "testuser",
                    "email": "test@example.com",
                    "password": password,
                    "confirm_password": password
                },
                headers={"Content-Type": "application/json"})
            print(f"    Password: {password} -> Status: {response.status_code}")
        except Exception as e:
            print(f"    Error testing password: {e}")

def test_security_headers():
    """Test security headers"""
    print("\n🔒 Testing Security Headers...")
    
    try:
        response = requests.get(f"{BASE_URL}/")
        headers = response.headers
        
        security_headers = [
            "X-Content-Type-Options",
            "X-Frame-Options", 
            "X-XSS-Protection",
            "Strict-Transport-Security",
            "Content-Security-Policy",
            "Referrer-Policy"
        ]
        
        for header in security_headers:
            if header in headers:
                print(f"    ✅ {header}: {headers[header]}")
            else:
                print(f"    ❌ {header}: Missing")
                
    except Exception as e:
        print(f"    Error testing headers: {e}")

def test_rate_limiting():
    """Test rate limiting (basic test)"""
    print("\n🔒 Testing Rate Limiting...")
    
    print("  Making multiple rapid requests...")
    for i in range(5):
        try:
            response = requests.get(f"{BASE_URL}/")
            print(f"    Request {i+1}: Status {response.status_code}")
            time.sleep(0.1)  # Small delay
        except Exception as e:
            print(f"    Error in request {i+1}: {e}")

def main():
    """Run all security tests"""
    print("🛡️  Flavor Quest Security Testing")
    print("=" * 50)
    
    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/")
        if response.status_code != 200:
            print("❌ Server not responding properly")
            return
        print("✅ Server is running")
    except Exception as e:
        print(f"❌ Cannot connect to server: {e}")
        return
    
    # Run all tests
    test_security_headers()
    test_xss_protection()
    test_sql_injection_protection()
    test_csrf_protection()
    test_input_validation()
    test_rate_limiting()
    
    print("\n" + "=" * 50)
    print("🏁 Security testing completed!")
    print("\nNote: This is a basic test. For comprehensive security testing,")
    print("consider using specialized tools like OWASP ZAP or Burp Suite.")

if __name__ == "__main__":
    main()
