# Security Testing Guide

## XSS Protection Testing

### 1. Test Input Sanitization
Try entering these malicious inputs in the search field:

**Basic XSS Attempts:**
```
<script>alert('XSS')</script>
<img src="x" onerror="alert('XSS')">
javascript:alert('XSS')
<svg onload="alert('XSS')">
```

**Advanced XSS Attempts:**
```
"><script>alert('XSS')</script>
'><script>alert('XSS')</script>
"><img src=x onerror=alert('XSS')>
'><img src=x onerror=alert('XSS')>
```

### 2. Test in Different Fields
- **Search Query**: Try XSS in restaurant search
- **Review Text**: Try XSS in restaurant reviews
- **Username**: Try XSS in signup/login
- **Email**: Try XSS in email field

### 3. Expected Behavior
- All HTML tags should be escaped and displayed as text
- No JavaScript should execute
- Special characters should be properly encoded

## SQL Injection Protection Testing

### 1. Test Basic SQL Injection
Try these in search fields:

**Basic SQL Injection:**
```
'; DROP TABLE restaurants; --
' OR '1'='1
' UNION SELECT * FROM users --
admin'--
```

**Advanced SQL Injection:**
```
' OR 1=1 --
' OR 'x'='x
' AND (SELECT COUNT(*) FROM users) > 0 --
' UNION SELECT username, password FROM users --
```

### 2. Test in Different Endpoints
- **Search**: `/google-search`
- **Login**: `/login`
- **Signup**: `/signup`
- **Rating**: `/restaurants/{id}/rate`

### 3. Expected Behavior
- No database errors should occur
- Input should be treated as literal text
- No unauthorized data access
- Proper error messages (not database errors)

## CSRF Protection Testing

### 1. Test CSRF Token Validation
- Try making requests without CSRF tokens
- Try making requests with invalid CSRF tokens
- Try making requests with expired CSRF tokens

### 2. Expected Behavior
- Requests without valid CSRF tokens should be rejected
- Error messages should indicate CSRF validation failure

## Rate Limiting Testing

### 1. Test Rate Limits
- Make rapid requests to any endpoint
- Try to exceed the rate limit (100 requests per hour)

### 2. Expected Behavior
- After exceeding rate limit, requests should be rejected
- Proper rate limit error messages

## Input Validation Testing

### 1. Test Email Validation
```
invalid-email
test@
@domain.com
test@domain
test@domain.
```

### 2. Test Username Validation
```
a (too short)
verylongusernamethatexceedslimit (too long)
user@name (invalid characters)
```

### 3. Test Password Validation
```
123 (too short, no uppercase, no lowercase)
password (no numbers, no uppercase)
PASSWORD (no numbers, no lowercase)
Password (no numbers)
```

### 4. Test Rating Validation
```
0 (below minimum)
6 (above maximum)
-1 (negative)
abc (non-numeric)
```

## Security Headers Testing

### 1. Check Response Headers
Use browser developer tools or curl to check for:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Strict-Transport-Security: max-age=31536000; includeSubDomains`
- `Content-Security-Policy: default-src 'self'`
- `Referrer-Policy: strict-origin-when-cross-origin`

## Manual Testing Commands

### 1. Test XSS Protection
```bash
# Test search endpoint
curl -X POST http://localhost:5002/google-search \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"query": "<script>alert(\"XSS\")</script>", "location": "test"}'

# Test rating endpoint
curl -X POST http://localhost:5002/restaurants/1/rate \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "X-CSRF-Token: YOUR_CSRF_TOKEN" \
  -d '{"rating": 5, "review": "<img src=x onerror=alert(\"XSS\")>"}'
```

### 2. Test SQL Injection Protection
```bash
# Test search endpoint
curl -X POST http://localhost:5002/google-search \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"query": "restaurants", "location": "test\"; DROP TABLE restaurants; --"}'

# Test login endpoint
curl -X POST http://localhost:5002/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@test.com", "password": "password\"; DROP TABLE users; --"}'
```

### 3. Test CSRF Protection
```bash
# Test without CSRF token
curl -X POST http://localhost:5002/restaurants/1/rate \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"rating": 5, "review": "test"}'

# Test with invalid CSRF token
curl -X POST http://localhost:5002/restaurants/1/rate \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "X-CSRF-Token: invalid_token" \
  -d '{"rating": 5, "review": "test"}'
```

## Automated Testing Script

You can also create automated tests to verify these protections work correctly.

## What to Look For

### ✅ Good Signs (Protection Working)
- Input is sanitized and displayed as text
- No JavaScript execution
- No database errors
- Proper validation error messages
- CSRF token validation errors
- Rate limiting responses

### ❌ Bad Signs (Protection Not Working)
- JavaScript executes in browser
- Database errors in logs
- Unauthorized data access
- Missing security headers
- No input validation

## Reporting Issues

If you find any security vulnerabilities:
1. Document the exact input that caused the issue
2. Note the endpoint and method used
3. Describe the expected vs actual behavior
4. Include any error messages or logs
