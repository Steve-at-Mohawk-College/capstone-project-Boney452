#!/bin/bash
# Quick OWASP ZAP Full Scan Script
# Runs all security tests and generates combined report

TARGET_URL="https://flavour-quest-e7ho.onrender.com"
REPORT_NAME="flavor-quest-security-report-$(date +%Y%m%d-%H%M%S)"
ZAP_HOST="localhost"
ZAP_PORT="8080"

echo "============================================================"
echo "OWASP ZAP Full Security Scan - Flavor Quest"
echo "============================================================"
echo "Target: $TARGET_URL"
echo "Report: $REPORT_NAME"
echo "============================================================"

# Check if ZAP is running
echo ""
echo "[1/5] Checking ZAP connection..."
if ! curl -s "http://${ZAP_HOST}:${ZAP_PORT}/JSON/core/view/version/" > /dev/null; then
    echo "✗ ZAP is not running!"
    echo ""
    echo "Please start ZAP in daemon mode:"
    echo "  zap.sh -daemon -host 0.0.0.0 -port ${ZAP_PORT} -config api.disablekey=true"
    exit 1
fi
echo "✓ ZAP is running"

# Start Spider Scan
echo ""
echo "[2/5] Starting Spider Scan..."
SPIDER_RESPONSE=$(curl -s "http://${ZAP_HOST}:${ZAP_PORT}/JSON/spider/action/scan/?url=${TARGET_URL}&maxChildren=10&recurse=true")
SPIDER_ID=$(echo $SPIDER_RESPONSE | grep -o '"scan":"[0-9]*"' | grep -o '[0-9]*')

if [ -z "$SPIDER_ID" ]; then
    echo "✗ Error starting spider scan"
    exit 1
fi

echo "  Spider Scan ID: $SPIDER_ID"
echo "  Waiting for spider to complete..."

# Wait for spider to complete
SPIDER_STATUS="0"
while [ "$SPIDER_STATUS" -lt "100" ]; do
    sleep 5
    SPIDER_STATUS=$(curl -s "http://${ZAP_HOST}:${ZAP_PORT}/JSON/spider/view/status/?scanId=${SPIDER_ID}" | grep -o '"status":"[0-9]*"' | grep -o '[0-9]*')
    if [ -z "$SPIDER_STATUS" ]; then
        SPIDER_STATUS="0"
    fi
    echo "  Spider Progress: ${SPIDER_STATUS}%"
done
echo "✓ Spider Scan Complete"

# Start Active Scan
echo ""
echo "[3/5] Starting Active Scan..."
echo "  ⚠️  This may take 30-60 minutes..."
ACTIVE_RESPONSE=$(curl -s "http://${ZAP_HOST}:${ZAP_PORT}/JSON/ascan/action/scan/?url=${TARGET_URL}&recurse=true&inScopeOnly=false")
ACTIVE_ID=$(echo $ACTIVE_RESPONSE | grep -o '"scan":"[0-9]*"' | grep -o '[0-9]*')

if [ -z "$ACTIVE_ID" ]; then
    echo "✗ Error starting active scan"
    exit 1
fi

echo "  Active Scan ID: $ACTIVE_ID"
echo "  Waiting for active scan to complete..."

# Wait for active scan to complete
ACTIVE_STATUS="0"
while [ "$ACTIVE_STATUS" -lt "100" ]; do
    sleep 10
    ACTIVE_STATUS=$(curl -s "http://${ZAP_HOST}:${ZAP_PORT}/JSON/ascan/view/status/?scanId=${ACTIVE_ID}" | grep -o '"status":"[0-9]*"' | grep -o '[0-9]*')
    if [ -z "$ACTIVE_STATUS" ]; then
        ACTIVE_STATUS="0"
    fi
    echo "  Active Scan Progress: ${ACTIVE_STATUS}%"
done
echo "✓ Active Scan Complete"

# Generate Reports
echo ""
echo "[4/5] Generating Reports..."

# HTML Report
echo "  Generating HTML report..."
curl -s "http://${ZAP_HOST}:${ZAP_PORT}/OTHER/core/other/htmlreport/" > "${REPORT_NAME}.html"
if [ -f "${REPORT_NAME}.html" ]; then
    echo "  ✓ HTML Report: ${REPORT_NAME}.html"
else
    echo "  ✗ Failed to generate HTML report"
fi

# XML Report
echo "  Generating XML report..."
curl -s "http://${ZAP_HOST}:${ZAP_PORT}/OTHER/core/other/xmlreport/" > "${REPORT_NAME}.xml"
if [ -f "${REPORT_NAME}.xml" ]; then
    echo "  ✓ XML Report: ${REPORT_NAME}.xml"
else
    echo "  ✗ Failed to generate XML report"
fi

# JSON Report
echo "  Generating JSON report..."
curl -s "http://${ZAP_HOST}:${ZAP_PORT}/JSON/core/view/alerts/?baseurl=${TARGET_URL}" > "${REPORT_NAME}.json"
if [ -f "${REPORT_NAME}.json" ]; then
    echo "  ✓ JSON Report: ${REPORT_NAME}.json"
else
    echo "  ✗ Failed to generate JSON report"
fi

# Summary
echo ""
echo "[5/5] Scan Complete!"
echo "============================================================"
echo "Reports generated:"
echo "  - ${REPORT_NAME}.html (Open in browser for detailed view)"
echo "  - ${REPORT_NAME}.xml"
echo "  - ${REPORT_NAME}.json"
echo ""
echo "Next Steps:"
echo "1. Open ${REPORT_NAME}.html in your browser"
echo "2. Review High and Medium risk vulnerabilities"
echo "3. Address security issues"
echo "4. Re-run scan to verify fixes"
echo "============================================================"








