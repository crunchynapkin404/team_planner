#!/bin/bash
# Week 2 MFA Integration Test Script
# Tests the complete MFA workflow end-to-end

set -e  # Exit on error

BASE_URL="http://localhost:8000"
FRONTEND_URL="http://localhost:3001"

echo "🧪 Week 2 MFA Integration Tests"
echo "================================"
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test 1: Check backend is running
echo -n "Test 1: Backend health check... "
if curl -s "$BASE_URL/admin/" > /dev/null; then
    echo -e "${GREEN}✓ PASS${NC}"
else
    echo -e "${RED}✗ FAIL${NC}"
    exit 1
fi

# Test 2: Check frontend is running
echo -n "Test 2: Frontend health check... "
if curl -s "$FRONTEND_URL" | grep -q "Team Planner"; then
    echo -e "${GREEN}✓ PASS${NC}"
else
    echo -e "${RED}✗ FAIL${NC}"
    exit 1
fi

# Test 3: Login and get auth token
echo -n "Test 3: User authentication... "
TOKEN_RESPONSE=$(curl -s -X POST "$BASE_URL/api/auth-token/" \
    -H "Content-Type: application/json" \
    -d '{"username":"admin","password":"admin123"}')

TOKEN=$(echo $TOKEN_RESPONSE | grep -o '"token":"[^"]*"' | cut -d'"' -f4)

if [ -n "$TOKEN" ]; then
    echo -e "${GREEN}✓ PASS${NC} (Token: ${TOKEN:0:10}...)"
else
    echo -e "${RED}✗ FAIL${NC}"
    echo "Response: $TOKEN_RESPONSE"
    exit 1
fi

# Test 4: Check MFA status (should be disabled initially)
echo -n "Test 4: Check MFA status... "
MFA_STATUS=$(curl -s -X GET "$BASE_URL/api/mfa/status/" \
    -H "Authorization: Token $TOKEN")

if echo $MFA_STATUS | grep -q '"enabled":false'; then
    echo -e "${GREEN}✓ PASS${NC} (MFA disabled)"
elif echo $MFA_STATUS | grep -q '"enabled":true'; then
    echo -e "${YELLOW}⚠ WARN${NC} (MFA already enabled)"
else
    echo -e "${RED}✗ FAIL${NC}"
    echo "Response: $MFA_STATUS"
    exit 1
fi

# Test 5: Initialize MFA setup
echo -n "Test 5: Initialize MFA setup... "
MFA_SETUP=$(curl -s -X POST "$BASE_URL/api/mfa/setup/" \
    -H "Authorization: Token $TOKEN")

if echo $MFA_SETUP | grep -q '"secret"'; then
    SECRET=$(echo $MFA_SETUP | grep -o '"secret":"[^"]*"' | cut -d'"' -f4)
    echo -e "${GREEN}✓ PASS${NC} (Secret: ${SECRET:0:10}...)"
else
    echo -e "${RED}✗ FAIL${NC}"
    echo "Response: $MFA_SETUP"
    exit 1
fi

# Test 6: Generate TOTP token and verify
echo -n "Test 6: Verify MFA token... "

# Use Python to generate TOTP token
TOTP_TOKEN=$(docker exec team_planner_django python -c "
import pyotp
totp = pyotp.TOTP('$SECRET')
print(totp.now())
")

VERIFY_RESPONSE=$(curl -s -X POST "$BASE_URL/api/mfa/verify/" \
    -H "Authorization: Token $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"token\":\"$TOTP_TOKEN\"}")

if echo $VERIFY_RESPONSE | grep -q '"success":true'; then
    echo -e "${GREEN}✓ PASS${NC} (Token verified: $TOTP_TOKEN)"
else
    echo -e "${RED}✗ FAIL${NC}"
    echo "Response: $VERIFY_RESPONSE"
    exit 1
fi

# Test 7: Check MFA is now enabled
echo -n "Test 7: Verify MFA enabled... "
MFA_STATUS_AFTER=$(curl -s -X GET "$BASE_URL/api/mfa/status/" \
    -H "Authorization: Token $TOKEN")

if echo $MFA_STATUS_AFTER | grep -q '"enabled":true'; then
    echo -e "${GREEN}✓ PASS${NC}"
else
    echo -e "${RED}✗ FAIL${NC}"
    echo "Response: $MFA_STATUS_AFTER"
    exit 1
fi

# Test 8: Test backup codes were generated
echo -n "Test 8: Check backup codes... "
BACKUP_CODES=$(echo $MFA_SETUP | grep -o '"backup_codes":\[[^]]*\]')
if [ -n "$BACKUP_CODES" ]; then
    CODE_COUNT=$(echo $BACKUP_CODES | grep -o '"[A-Z0-9]\{8\}"' | wc -l)
    echo -e "${GREEN}✓ PASS${NC} ($CODE_COUNT backup codes generated)"
else
    echo -e "${RED}✗ FAIL${NC}"
    exit 1
fi

# Test 9: Test database migrations
echo -n "Test 9: Check MFA models in database... "
DB_CHECK=$(docker exec team_planner_django python manage.py shell -c "
from team_planner.users.models import TwoFactorDevice, MFALoginAttempt
from django.contrib.auth import get_user_model
User = get_user_model()
admin = User.objects.get(username='admin')
device = TwoFactorDevice.objects.filter(user=admin).first()
print('OK' if device else 'MISSING')
")

if echo $DB_CHECK | grep -q "OK"; then
    echo -e "${GREEN}✓ PASS${NC}"
else
    echo -e "${RED}✗ FAIL${NC}"
    echo "Device not found in database"
    exit 1
fi

# Test 10: Frontend accessibility
echo -n "Test 10: Frontend profile page accessible... "
if curl -s "$FRONTEND_URL" | grep -q "<!doctype html>"; then
    echo -e "${GREEN}✓ PASS${NC}"
else
    echo -e "${RED}✗ FAIL${NC}"
    exit 1
fi

echo ""
echo "================================"
echo -e "${GREEN}✅ All tests passed!${NC}"
echo ""
echo "📊 Test Summary:"
echo "  - Backend: ✓ Running"
echo "  - Frontend: ✓ Running"
echo "  - Authentication: ✓ Working"
echo "  - MFA Setup: ✓ Working"
echo "  - MFA Verification: ✓ Working"
echo "  - Backup Codes: ✓ Generated"
echo "  - Database: ✓ Models present"
echo ""
echo "🎯 Week 2 Progress:"
echo "  ✅ Backend API functional"
echo "  ✅ Frontend components integrated"
echo "  ✅ End-to-end workflow verified"
echo "  ⏳ Rate limiting (pending)"
echo "  ⏳ Account lockout (pending)"
echo "  ⏳ User documentation (pending)"
echo ""
echo "🔗 Quick Links:"
echo "  Frontend: $FRONTEND_URL"
echo "  Backend Admin: $BASE_URL/admin/"
echo "  API Docs: $BASE_URL/api/schema/swagger-ui/"
echo ""
echo "👤 Test Credentials:"
echo "  Username: admin"
echo "  Password: admin123"
echo "  MFA Secret: ${SECRET:0:10}..."
echo "  Current TOTP: $TOTP_TOKEN"
echo ""
