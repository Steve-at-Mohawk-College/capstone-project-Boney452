# Manual Security Testing Guide

## 🧪 How to Test XSS/SQL Injection Protections Manually

### 1. **XSS Protection Testing**

#### Test in Search Field:
1. Go to the search page
2. Try entering these malicious inputs:
   ```
   <script>alert('XSS')</script>
   <img src="x" onerror="alert('XSS')">
   javascript:alert('XSS')
   <svg onload="alert('XSS')">
   ```

#### Test in Review Field:
1. Search for a restaurant
2. Flip the card to the back
3. Try entering XSS payloads in the review textarea
4. Submit the review

#### Expected Results:
- ✅ No JavaScript should execute
- ✅ HTML tags should be displayed as text
- ✅ Special characters should be escaped

### 2. **SQL Injection Protection Testing**

#### Test in Search Field:
1. Go to the search page
2. Try entering these SQL injection attempts:
   ```
   '; DROP TABLE restaurants; --
   ' OR '1'='1
   ' UNION SELECT * FROM users --
   admin'--
   ' OR 1=1 --
   ```

#### Test in Login Field:
1. Go to the login page
2. Try SQL injection in email/password fields

#### Expected Results:
- ✅ No database errors should occur
- ✅ Input should be treated as literal text
- ✅ No unauthorized data access

### 3. **CSRF Protection Testing**

#### Test Rating Submission:
1. Login to your account
2. Search for a restaurant
3. Try to submit a rating without proper CSRF token
4. Check browser developer tools for CSRF errors

#### Expected Results:
- ✅ Requests without CSRF tokens should be rejected
- ✅ Error messages should indicate CSRF validation failure

### 4. **Input Validation Testing**

#### Test Email Validation:
1. Go to signup page
2. Try these invalid emails:
   ```
   invalid-email
   test@
   @domain.com
   test@domain
   ```

#### Test Password Validation:
1. Go to signup page
2. Try these weak passwords:
   ```
   123
   password
   PASSWORD
   Password
   ```

#### Test Rating Validation:
1. Try to submit ratings outside 1-5 range:
   ```
   0
   6
   -1
   abc
   ```

#### Expected Results:
- ✅ Invalid inputs should be rejected
- ✅ Proper validation error messages should appear

### 5. **Security Headers Testing**

#### Check Response Headers:
1. Open browser developer tools (F12)
2. Go to Network tab
3. Make any request to the website
4. Check the response headers for:
   - `X-Content-Type-Options: nosniff`
   - `X-Frame-Options: DENY`
   - `X-XSS-Protection: 1; mode=block`
   - `Strict-Transport-Security: max-age=31536000; includeSubDomains`
   - `Content-Security-Policy: default-src 'self'`
   - `Referrer-Policy: strict-origin-when-cross-origin`

### 6. **Rate Limiting Testing**

#### Test Rapid Requests:
1. Make many rapid requests to any endpoint
2. Try to exceed the rate limit (100 requests per hour)
3. Check for rate limiting responses

#### Expected Results:
- ✅ After exceeding rate limit, requests should be rejected
- ✅ Proper rate limit error messages

## 🔍 What to Look For

### ✅ **Good Signs (Protection Working)**
- Input is sanitized and displayed as text
- No JavaScript execution in browser
- No database errors in browser console or server logs
- Proper validation error messages
- CSRF token validation errors
- Rate limiting responses
- Security headers present

### ❌ **Bad Signs (Protection Not Working)**
- JavaScript executes in browser
- Database errors appear in console/logs
- Unauthorized data access
- Missing security headers
- No input validation
- CSRF attacks succeed

## 🛠️ **Browser Developer Tools Testing**

### Console Testing:
1. Open browser console (F12 → Console)
2. Try executing JavaScript:
   ```javascript
   alert('XSS Test')
   document.cookie
   localStorage.getItem('token')
   ```

### Network Tab Testing:
1. Go to Network tab in developer tools
2. Make requests and check:
   - Response headers for security headers
   - Request/response bodies for data leakage
   - Status codes for proper error handling

### Application Tab Testing:
1. Go to Application tab
2. Check:
   - Local Storage for sensitive data
   - Session Storage for session management
   - Cookies for secure flags

## 📊 **Test Results Summary**

After running these tests, you should see:

| Protection Type | Status | Evidence |
|----------------|--------|----------|
| XSS Protection | ✅ Working | No script execution, HTML escaped |
| SQL Injection | ✅ Working | No database errors, input sanitized |
| CSRF Protection | ✅ Working | 403 errors for invalid/missing tokens |
| Input Validation | ✅ Working | Proper validation error messages |
| Security Headers | ✅ Working | All headers present in responses |
| Rate Limiting | ✅ Working | Requests rejected after limit |

## 🚨 **If You Find Issues**

1. **Document the exact input** that caused the issue
2. **Note the endpoint and method** used
3. **Describe the expected vs actual behavior**
4. **Include any error messages or logs**
5. **Test in different browsers** to confirm

## 🔧 **Advanced Testing Tools**

For more comprehensive testing, consider:
- **OWASP ZAP** - Free security scanner
- **Burp Suite** - Professional web security testing
- **Nessus** - Vulnerability scanner
- **SQLMap** - SQL injection testing tool
