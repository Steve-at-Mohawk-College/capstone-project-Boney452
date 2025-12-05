#!/usr/bin/env python3
"""
OWASP ZAP Full Security Scan Script
Runs all tests automatically and generates combined report
"""

import time
import requests
import json
from datetime import datetime
import sys

# Configuration
ZAP_URL = "http://localhost:8080"
TARGET_URL = "https://flavour-quest-e7ho.onrender.com"
API_KEY = None  # Set if API key is enabled

def zap_request(endpoint, params=None):
    """Make request to ZAP API"""
    url = f"{ZAP_URL}{endpoint}"
    if API_KEY:
        params = params or {}
        params['apikey'] = API_KEY
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response
    except requests.exceptions.RequestException as e:
        print(f"Error making request to ZAP: {e}")
        print("Make sure ZAP is running in daemon mode:")
        print("  zap.sh -daemon -host 0.0.0.0 -port 8080 -config api.disablekey=true")
        sys.exit(1)

def wait_for_scan_completion(scan_type, scan_id):
    """Wait for scan to complete"""
    print(f"\nWaiting for {scan_type} scan to complete...")
    last_progress = -1
    while True:
        try:
            if scan_type == "spider":
                response = zap_request("/JSON/spider/view/status/", {"scanId": scan_id})
            else:
                response = zap_request("/JSON/ascan/view/status/", {"scanId": scan_id})
            
            status = response.json()
            progress = int(status.get("status", 0))
            
            if progress != last_progress:
                print(f"  {scan_type.upper()} Progress: {progress}%")
                last_progress = progress
            
            if progress >= 100:
                break
            time.sleep(5)
        except KeyboardInterrupt:
            print("\n\nScan interrupted by user")
            sys.exit(1)
        except Exception as e:
            print(f"Error checking scan status: {e}")
            time.sleep(5)

def main():
    print("=" * 70)
    print("OWASP ZAP Full Security Scan - Flavor Quest")
    print("=" * 70)
    print(f"Target URL: {TARGET_URL}")
    print(f"ZAP URL: {ZAP_URL}")
    print("=" * 70)
    
    # Check ZAP is running
    print("\n[0/5] Checking ZAP connection...")
    try:
        response = zap_request("/JSON/core/view/version/")
        version = response.json().get("version", "Unknown")
        print(f"✓ ZAP is running (Version: {version})")
    except:
        print("✗ Cannot connect to ZAP")
        print("\nPlease start ZAP in daemon mode:")
        print("  zap.sh -daemon -host 0.0.0.0 -port 8080 -config api.disablekey=true")
        sys.exit(1)
    
    # 1. Start Spider Scan
    print("\n[1/5] Starting Spider Scan...")
    print("  This will discover all URLs in your application...")
    response = zap_request("/JSON/spider/action/scan/", {
        "url": TARGET_URL,
        "maxChildren": 10,
        "recurse": "true"
    })
    spider_result = response.json()
    if "scan" in spider_result:
        spider_id = spider_result.get("scan")
        print(f"  Spider Scan ID: {spider_id}")
        wait_for_scan_completion("spider", spider_id)
        print("✓ Spider Scan Complete")
    else:
        print(f"✗ Error starting spider scan: {spider_result}")
        sys.exit(1)
    
    # Get spider results
    spider_results = zap_request("/JSON/spider/view/results/", {"scanId": spider_id})
    urls_found = len(spider_results.json().get("results", []))
    print(f"  URLs discovered: {urls_found}")
    
    # 2. Start Active Scan
    print("\n[2/5] Starting Active Scan...")
    print("  This will test for vulnerabilities (XSS, SQL Injection, etc.)...")
    print("  ⚠️  This may take 30-60 minutes depending on application size...")
    response = zap_request("/JSON/ascan/action/scan/", {
        "url": TARGET_URL,
        "recurse": "true",
        "inScopeOnly": "false"
    })
    active_result = response.json()
    if "scan" in active_result:
        active_id = active_result.get("scan")
        print(f"  Active Scan ID: {active_id}")
        wait_for_scan_completion("ascan", active_id)
        print("✓ Active Scan Complete")
    else:
        print(f"✗ Error starting active scan: {active_result}")
        sys.exit(1)
    
    # 3. Get Alerts Summary
    print("\n[3/5] Collecting Results...")
    alerts_response = zap_request("/JSON/core/view/alerts/", {"baseurl": TARGET_URL})
    alerts = alerts_response.json().get("alerts", [])
    
    # Count by risk level
    risk_counts = {"High": 0, "Medium": 0, "Low": 0, "Informational": 0}
    for alert in alerts:
        risk = alert.get("risk", "Informational")
        risk_counts[risk] = risk_counts.get(risk, 0) + 1
    
    # Count by alert type
    alert_types = {}
    for alert in alerts:
        alert_name = alert.get("name", "Unknown")
        alert_types[alert_name] = alert_types.get(alert_name, 0) + 1
    
    print("\n" + "=" * 70)
    print("SCAN RESULTS SUMMARY")
    print("=" * 70)
    print(f"High Risk:        {risk_counts['High']}")
    print(f"Medium Risk:      {risk_counts['Medium']}")
    print(f"Low Risk:         {risk_counts['Low']}")
    print(f"Informational:    {risk_counts['Informational']}")
    print(f"Total Alerts:     {len(alerts)}")
    print("=" * 70)
    
    if risk_counts['High'] > 0 or risk_counts['Medium'] > 0:
        print("\n⚠️  HIGH PRIORITY: Address High and Medium risk issues immediately!")
    
    # Show top alert types
    if alert_types:
        print("\nTop Alert Types:")
        sorted_types = sorted(alert_types.items(), key=lambda x: x[1], reverse=True)[:10]
        for alert_name, count in sorted_types:
            print(f"  - {alert_name}: {count}")
    
    # 4. Generate Reports
    print("\n[4/5] Generating Reports...")
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    
    # HTML Report (Most detailed)
    try:
        html_response = zap_request("/OTHER/core/other/htmlreport/")
        html_filename = f"flavor-quest-security-report-{timestamp}.html"
        with open(html_filename, "w", encoding="utf-8") as f:
            f.write(html_response.text)
        print(f"✓ HTML Report: {html_filename}")
    except Exception as e:
        print(f"✗ Error generating HTML report: {e}")
    
    # XML Report
    try:
        xml_response = zap_request("/OTHER/core/other/xmlreport/")
        xml_filename = f"flavor-quest-security-report-{timestamp}.xml"
        with open(xml_filename, "w", encoding="utf-8") as f:
            f.write(xml_response.text)
        print(f"✓ XML Report: {xml_filename}")
    except Exception as e:
        print(f"✗ Error generating XML report: {e}")
    
    # JSON Report (Machine readable)
    try:
        json_filename = f"flavor-quest-security-report-{timestamp}.json"
        with open(json_filename, "w", encoding="utf-8") as f:
            json.dump(alerts_response.json(), f, indent=2)
        print(f"✓ JSON Report: {json_filename}")
    except Exception as e:
        print(f"✗ Error generating JSON report: {e}")
    
    # Markdown Report (if available)
    try:
        md_response = zap_request("/OTHER/core/other/markdownreport/")
        md_filename = f"flavor-quest-security-report-{timestamp}.md"
        with open(md_filename, "w", encoding="utf-8") as f:
            f.write(md_response.text)
        print(f"✓ Markdown Report: {md_filename}")
    except:
        pass  # Markdown report may not be available in all ZAP versions
    
    # 5. Summary
    print("\n[5/5] Scan Complete!")
    print("=" * 70)
    print(f"All reports saved with timestamp: {timestamp}")
    print("\nNext Steps:")
    print("1. Open HTML report in browser for detailed findings")
    print("2. Review High and Medium risk vulnerabilities first")
    print("3. Address security issues")
    print("4. Re-run scan to verify fixes")
    print("=" * 70)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nScan interrupted by user. Partial results may be available.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nError during scan: {e}")
        sys.exit(1)







