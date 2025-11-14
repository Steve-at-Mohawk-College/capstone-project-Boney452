# OWASP ZAP Security Testing Guide - Flavor Quest

This document provides comprehensive instructions for conducting security testing of the Flavor Quest application using OWASP ZAP (Zed Attack Proxy).

## 📋 Table of Contents

1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Testing Procedures](#testing-procedures)
5. [Vulnerability Testing](#vulnerability-testing)
6. [Interpreting Results](#interpreting-results)
7. [Remediation](#remediation)
8. [Best Practices](#best-practices)

---

## 🔍 Introduction

### What is OWASP ZAP?

OWASP ZAP (Zed Attack Proxy) is a free, open-source security testing tool used to find vulnerabilities in web applications. It's designed to be used by both those new to application security and professional penetration testers.

### Why Use OWASP ZAP?

- **Automated Scanning**: Automatically finds common vulnerabilities
- **Manual Testing Support**: Allows manual exploration and testing
- **API Testing**: Supports REST API security testing
- **Comprehensive Reports**: Generates detailed security reports
- **OWASP Top 10 Coverage**: Tests for OWASP Top 10 vulnerabilities

### Flavor Quest Application Endpoints

**Frontend**: `https://flavourquestcap.netlify.app`  
**Backend API**: `https://flavour-quest-e7ho.onrender.com`

---

## 📥 Installation

### Option 1: Download Standalone Application

1. Visit [OWASP ZAP Downloads](https://www.zaproxy.org/download/)
2. Download ZAP for your operating system:
   - **Windows**: `ZAP_Windows_2.x.x.exe`
   - **macOS**: `ZAP_macOS_2.x.x.dmg`
   - **Linux**: `ZAP_2.x.x_Linux.tar.gz`
3. Install following the platform-specific instructions

### Option 2: Docker (Recommended for CI/CD)

```bash
docker pull owasp/zap2docker-stable
docker run -t owasp/zap2docker-stable zap-baseline.py -t https://flavourquestcap.netlify.app
```

### Option 3: Command Line (Linux/macOS)

```bash
# Using Homebrew (macOS)
brew install --cask owasp-zap

# Using apt (Linux)
sudo apt-get install zaproxy
```

---

## ⚙️ Configuration

### 1. Initial Setup

1. **Launch OWASP ZAP**
2. Choose **"I don't want to persist this session"** for testing (or create a session for tracking)
3. Click **"Start"**

### 2. Configure Target Application

#### For Frontend Testing:
- **URL**: `https://flavourquestcap.netlify.app`
- **Context**: Create a new context named "FlavorQuest-Frontend"

#### For Backend API Testing:
- **Base URL**: `https://flavour-quest-e7ho.onrender.com`
- **Context**: Create a new context named "FlavorQuest-API"

### 3. Authentication Setup

Since Flavor Quest requires authentication, configure ZAP to handle login:

#### Step 1: Manual Authentication
1. Open ZAP's browser (Tools → Manual Request Editor)
2. Navigate to the login page
3. Perform a manual login to capture the authentication flow

#### Step 2: Configure Authentication Method
1. Go to **Tools → Options → Authentication**
2. Select **"Manual Authentication"**
3. Configure the authentication request:
   - **Login URL**: `https://flavour-quest-e7ho.onrender.com/login`
   - **Login Request Data**: 
     ```json
     {
       "email": "test@example.com",
       "password": "TestPassword123"
     }
     ```
   - **Logged in indicator**: Look for `"token"` in response
   - **Logged out indicator**: HTTP 401 status

#### Step 3: Configure Session Management
1. Go to **Tools → Options → Session Management**
2. Select **"Cookie-Based Session Management"**
3. Add session token handling:
   - **Token name**: `token`
   - **Token location**: HTTP Header (`Authorization: Bearer <token>`)

### 4. Configure Spider Settings

1. Go to **Tools → Options → Spider**
2. Configure:
   - **Max Depth**: 5
   - **Max Children**: 100
   - **Thread Count**: 5
   - **User Agent**: Set to a modern browser user agent

### 5. Configure Active Scan Settings

1. Go to **Tools → Options → Active Scan**
2. Enable all scan policies:
   - SQL Injection
   - XSS (Cross-Site Scripting)
   - CSRF
   - Authentication Bypass
   - Path Traversal
   - Command Injection

---

## 🧪 Testing Procedures

### Phase 1: Passive Scanning

Passive scanning analyzes traffic without modifying requests.

#### Steps:
1. **Start Proxy**
   - ZAP runs as a proxy on port 8080 by default
   - Configure browser to use proxy: `127.0.0.1:8080`

2. **Browse Application**
   - Navigate through all pages:
     - Landing page
     - Login
     - Signup
     - Restaurant search
     - Restaurant rating
     - Chat system
     - User management (if admin)

3. **Review Alerts**
   - Check **Alerts** tab in ZAP
   - Review passive scan findings
   - Note any information disclosure issues

### Phase 2: Spider Scanning

Spider scanning crawls the application to discover all pages and endpoints.

#### Steps:
1. **Right-click on target site** in Sites tree
2. Select **"Attack → Spider"**
3. Configure spider:
   - **Max Depth**: 5
   - **Max Children**: 100
4. **Start Spider**
5. **Monitor Progress** in Spider tab
6. **Review Discovered URLs** in Sites tree

### Phase 3: Active Scanning

Active scanning sends malicious payloads to test for vulnerabilities.

#### Steps:
1. **Right-click on target site** in Sites tree
2. Select **"Attack → Active Scan"**
3. Configure scan:
   - **Scan Policy**: Default Policy (or create custom)
   - **Scope**: Entire site or specific subtree
4. **Start Active Scan**
5. **Monitor Progress** in Active Scan tab
6. **Review Alerts** as they appear

### Phase 4: Manual Testing

Manual testing allows you to test specific vulnerabilities.

#### Common Manual Tests:

1. **XSS Testing**
   - Test all input fields with: `<script>alert('XSS')</script>`
   - Test with: `"><img src=x onerror=alert('XSS')>`
   - Check if payloads are reflected in responses

2. **SQL Injection Testing**
   - Test search fields with: `' OR '1'='1`
   - Test with: `'; DROP TABLE users; --`
   - Check for SQL error messages

3. **CSRF Testing**
   - Use ZAP's CSRF token finder
   - Test state-changing operations without tokens
   - Verify token validation

4. **Authentication Testing**
   - Test with invalid credentials
   - Test token expiration
   - Test token manipulation

---

## 🎯 Vulnerability Testing

### 1. SQL Injection

#### Test Cases:
```http
POST /google-search
Content-Type: application/json

{
  "query": "restaurants in ' OR '1'='1",
  "location": "Toronto"
}
```

#### Expected Result:
- Application should handle input safely
- No SQL error messages in responses
- Parameterized queries should prevent injection

### 2. Cross-Site Scripting (XSS)

#### Test Cases:
```http
POST /signup
Content-Type: application/json

{
  "username": "<script>alert('XSS')</script>",
  "email": "test@example.com",
  "password": "Test123"
}
```

#### Expected Result:
- Input should be sanitized
- Script tags should be escaped
- No script execution in browser

### 3. CSRF (Cross-Site Request Forgery)

#### Test Cases:
```http
POST /restaurants/1/rate
Content-Type: application/json
# Without CSRF token

{
  "rating": 5,
  "review_text": "Great food!"
}
```

#### Expected Result:
- Request should be rejected
- 403 Forbidden response
- CSRF token validation error

### 4. Authentication Bypass

#### Test Cases:
```http
GET /me
Authorization: Bearer invalid_token_here
```

#### Expected Result:
- 401 Unauthorized response
- No user data returned
- Proper token validation

### 5. Path Traversal

#### Test Cases:
```http
GET /restaurants/../../../etc/passwd
```

#### Expected Result:
- Request should be rejected
- No file system access
- Proper path validation

### 6. Command Injection

#### Test Cases:
```http
POST /google-search
Content-Type: application/json

{
  "query": "restaurants; cat /etc/passwd",
  "location": "Toronto"
}
```

#### Expected Result:
- Input should be sanitized
- No command execution
- Proper input validation

### 7. Sensitive Data Exposure

#### Check For:
- Passwords in responses
- API keys in client-side code
- Database credentials in error messages
- Tokens in URLs

### 8. Security Headers

#### Check For:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Strict-Transport-Security`
- `Content-Security-Policy`

---

## 📊 Interpreting Results

### Alert Levels

1. **High**: Critical vulnerabilities requiring immediate attention
   - SQL Injection
   - Remote Code Execution
   - Authentication Bypass

2. **Medium**: Important vulnerabilities that should be fixed
   - XSS (Reflected/Stored)
   - CSRF
   - Path Traversal

3. **Low**: Informational or minor issues
   - Missing security headers
   - Information disclosure
   - Weak cryptography

4. **Informational**: Best practices and recommendations
   - Cookie security
   - Cache control
   - Content type issues

### Common Alerts for Flavor Quest

#### Expected Findings (Should be Fixed):

1. **Missing Anti-CSRF Tokens**
   - **Risk**: Medium
   - **Location**: All POST/PUT/DELETE endpoints
   - **Fix**: Ensure CSRF tokens are present and validated

2. **XSS Vulnerabilities**
   - **Risk**: Medium to High
   - **Location**: User input fields
   - **Fix**: Implement proper input sanitization

3. **SQL Injection**
   - **Risk**: High
   - **Location**: Database queries
   - **Fix**: Use parameterized queries (already implemented)

4. **Missing Security Headers**
   - **Risk**: Low to Medium
   - **Location**: All HTTP responses
   - **Fix**: Add security headers (already implemented)

#### False Positives (Can be Ignored):

1. **Cookie Without Secure Flag** (if testing on HTTP)
2. **Content-Type Missing** (for some API responses)
3. **Cache-Control Missing** (for dynamic content)

---

## 🔧 Remediation

### For SQL Injection Findings:

**If Found**: Review all database queries
```python
# ✅ Correct - Already implemented
cur.execute("SELECT * FROM users WHERE email = %s", (email,))

# ❌ Incorrect - Should not exist
cur.execute(f"SELECT * FROM users WHERE email = '{email}'")
```

### For XSS Findings:

**If Found**: Enhance input sanitization
```javascript
// ✅ Already implemented
const sanitized = sanitizeInput(userInput, maxLength);
```

### For CSRF Findings:

**If Found**: Verify CSRF token implementation
```python
# ✅ Already implemented
@require_csrf
def create_group():
    # CSRF token validated
```

### For Missing Headers:

**If Found**: Add security headers
```python
# ✅ Already implemented
response.headers['X-Content-Type-Options'] = 'nosniff'
response.headers['X-Frame-Options'] = 'DENY'
```

---

## 📈 Generating Reports

### HTML Report

1. Go to **Report → Generate HTML Report**
2. Select scan results
3. Choose report format
4. Save report

### XML Report

1. Go to **Report → Generate XML Report**
2. Export for integration with other tools

### Command Line Report

```bash
# Generate baseline report
zap-baseline.py -t https://flavourquestcap.netlify.app -J zap-report.json

# Generate HTML report
zap-html.py -I baseline -o zap-report.html
```

---

## ✅ Best Practices

### 1. Regular Testing Schedule

- **Before Production Deployment**: Full scan
- **After Major Updates**: Active scan
- **Monthly**: Passive scan
- **Quarterly**: Comprehensive security audit

### 2. Test Environment

- Always test in a **staging environment** first
- Use **test accounts** with limited permissions
- **Never test** with production data

### 3. Scope Definition

- Define clear **testing scope**
- Include **all endpoints** in testing
- Test **authentication flows** thoroughly

### 4. Documentation

- **Document all findings**
- **Track remediation** progress
- **Maintain security reports** for compliance

### 5. Continuous Improvement

- **Review findings** regularly
- **Update test cases** based on new threats
- **Stay updated** with OWASP Top 10

---

## 🎓 OWASP ZAP Resources

### Official Documentation
- [OWASP ZAP User Guide](https://www.zaproxy.org/docs/)
- [OWASP ZAP API Documentation](https://www.zaproxy.org/docs/api/)

### Training
- [OWASP ZAP Getting Started](https://www.zaproxy.org/getting-started/)
- [OWASP ZAP Tutorials](https://www.zaproxy.org/docs/desktop/tutorials/)

### Community
- [OWASP ZAP GitHub](https://github.com/zaproxy/zaproxy)
- [OWASP ZAP Discussions](https://groups.google.com/group/zaproxy-users)

---

## 📝 Testing Checklist

### Pre-Testing
- [ ] OWASP ZAP installed and configured
- [ ] Test environment set up
- [ ] Test accounts created
- [ ] Authentication configured in ZAP
- [ ] Target URLs identified

### During Testing
- [ ] Passive scan completed
- [ ] Spider scan completed
- [ ] Active scan completed
- [ ] Manual testing performed
- [ ] All endpoints tested
- [ ] Authentication flows tested

### Post-Testing
- [ ] All alerts reviewed
- [ ] False positives identified
- [ ] Vulnerabilities documented
- [ ] Report generated
- [ ] Remediation plan created

---

## 🚨 Important Notes

1. **Ethical Testing**: Only test applications you own or have explicit permission to test
2. **Production Safety**: Never run active scans on production without proper safeguards
3. **Rate Limiting**: Be aware of rate limits to avoid disrupting service
4. **Data Privacy**: Do not test with real user data
5. **Documentation**: Keep detailed records of all testing activities

---

## 📞 Support

For issues or questions regarding security testing:
- Review OWASP ZAP documentation
- Check application security documentation (SECURITY.md)
- Consult with security team or advisor

---

**Last Updated**: 2025-01-13  
**Version**: 1.0  
**Maintained By**: Flavor Quest Development Team

