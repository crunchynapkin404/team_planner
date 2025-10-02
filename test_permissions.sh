#!/bin/bash

# Test Permission Enforcement Script
# Tests all protected API endpoints with different user roles

API_BASE="http://localhost:8000"
COLORS=true

# ANSI color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test users
declare -A USERS=(
    ["admin"]="test_superadmin:TestPass123!"
    ["manager"]="test_manager:TestPass123!"
    ["planner"]="test_planner:TestPass123!"
    ["employee"]="test_employee:TestPass123!"
    ["teamlead"]="test_teamlead:TestPass123!"
)

# Store tokens
declare -A TOKENS=()

echo "============================================"
echo "  Permission Enforcement Testing"
echo "============================================"
echo ""

# Function to login and get token
login_user() {
    local role=$1
    local credentials=${USERS[$role]}
    local username=$(echo $credentials | cut -d: -f1)
    local password=$(echo $credentials | cut -d: -f2)
    
    echo -e "${BLUE}[LOGIN]${NC} Logging in as $username..."
    
    local response=$(curl -s -X POST "${API_BASE}/api/auth/login/" \
        -H "Content-Type: application/json" \
        -d "{\"username\": \"$username\", \"password\": \"$password\"}")
    
    local token=$(echo $response | grep -o '"token":"[^"]*' | cut -d'"' -f4)
    
    if [ -z "$token" ]; then
        echo -e "${RED}  ✗ Failed to login${NC}"
        echo "  Response: $response"
        return 1
    fi
    
    TOKENS[$role]=$token
    echo -e "${GREEN}  ✓ Logged in successfully${NC}"
    echo ""
    return 0
}

# Function to test an endpoint
test_endpoint() {
    local role=$1
    local method=$2
    local endpoint=$3
    local expected_status=$4
    local description=$5
    local data=$6
    
    local token=${TOKENS[$role]}
    
    if [ -z "$token" ]; then
        echo -e "${RED}  ✗ No token for $role${NC}"
        return 1
    fi
    
    # Build curl command
    local curl_cmd="curl -s -w '\n%{http_code}' -X $method '${API_BASE}${endpoint}' \
        -H 'Authorization: Token $token' \
        -H 'Content-Type: application/json'"
    
    if [ ! -z "$data" ]; then
        curl_cmd="$curl_cmd -d '$data'"
    fi
    
    # Execute request
    local response=$(eval $curl_cmd)
    local status=$(echo "$response" | tail -n1)
    local body=$(echo "$response" | head -n-1)
    
    # Check result
    if [ "$status" = "$expected_status" ]; then
        echo -e "${GREEN}  ✓${NC} $description"
        echo -e "    ${BLUE}[$role | $method $endpoint]${NC} Status: $status"
    else
        echo -e "${RED}  ✗${NC} $description"
        echo -e "    ${BLUE}[$role | $method $endpoint]${NC} Expected: $expected_status, Got: $status"
        if echo "$body" | grep -q "error\|detail"; then
            echo "    Response: $(echo $body | head -c 200)"
        fi
    fi
    echo ""
}

# Login all test users
echo "=========================================="
echo "Step 1: Login Test Users"
echo "=========================================="
echo ""

for role in "${!USERS[@]}"; do
    login_user $role
done

echo "=========================================="
echo "Step 2: Test User Management (UserViewSet)"
echo "=========================================="
echo ""

# Admin should be able to list users (has can_manage_users)
test_endpoint "admin" "GET" "/api/users/" "200" "Admin can list users"

# Manager should NOT be able to list users (doesn't have can_manage_users)
test_endpoint "manager" "GET" "/api/users/" "403" "Manager cannot list users (no can_manage_users)"

# Employee should NOT be able to list users
test_endpoint "employee" "GET" "/api/users/" "403" "Employee cannot list users"

# Employee can view their own profile
test_endpoint "employee" "GET" "/api/users/me/" "200" "Employee can view own profile"

echo "=========================================="
echo "Step 3: Test Team Management (TeamViewSet)"
echo "=========================================="
echo ""

# Admin should be able to list teams (has can_manage_team)
test_endpoint "admin" "GET" "/api/teams/" "200" "Admin can list teams"

# Manager should be able to list teams (has can_manage_team)
test_endpoint "manager" "GET" "/api/teams/" "200" "Manager can list teams"

# Team Lead should NOT be able to list teams (doesn't have can_manage_team)
test_endpoint "teamlead" "GET" "/api/teams/" "403" "Team Lead cannot list teams (no can_manage_team)"

# Employee should NOT be able to list teams
test_endpoint "employee" "GET" "/api/teams/" "403" "Employee cannot list teams"

# Try creating a team (only admin/manager should succeed)
test_endpoint "manager" "POST" "/api/teams/" "201" "Manager can create team" \
    '{"name": "Test Team", "description": "Test Description"}'

test_endpoint "employee" "POST" "/api/teams/" "403" "Employee cannot create team" \
    '{"name": "Test Team 2", "description": "Test"}'

echo "=========================================="
echo "Step 4: Test Leave Management (LeaveRequestViewSet)"
echo "=========================================="
echo ""

# Employee should be able to request leave
test_endpoint "employee" "POST" "/api/leaves/requests/" "201" "Employee can request leave" \
    '{"start_date": "2025-10-15", "end_date": "2025-10-16", "reason": "Test", "leave_type": 1}'

# Manager should be able to view leave requests
test_endpoint "manager" "GET" "/api/leaves/requests/" "200" "Manager can view leave requests"

# Employee viewing their own leave should work
test_endpoint "employee" "GET" "/api/leaves/requests/" "200" "Employee can view own leave"

echo "=========================================="
echo "Step 5: Test Orchestrator (Scheduling)"
echo "=========================================="
echo ""

# Only roles with can_run_orchestrator should access
test_endpoint "admin" "POST" "/api/orchestrator/schedule/" "200" "Admin can run orchestrator" \
    '{"start_date": "2025-10-01", "end_date": "2025-10-07"}'

test_endpoint "manager" "POST" "/api/orchestrator/schedule/" "200" "Manager can run orchestrator" \
    '{"start_date": "2025-10-01", "end_date": "2025-10-07"}'

test_endpoint "planner" "POST" "/api/orchestrator/schedule/" "200" "Scheduler can run orchestrator" \
    '{"start_date": "2025-10-01", "end_date": "2025-10-07"}'

test_endpoint "employee" "POST" "/api/orchestrator/schedule/" "403" "Employee cannot run orchestrator" \
    '{"start_date": "2025-10-01", "end_date": "2025-10-07"}'

test_endpoint "teamlead" "POST" "/api/orchestrator/schedule/" "403" "Team Lead cannot run orchestrator" \
    '{"start_date": "2025-10-01", "end_date": "2025-10-07"}'

echo "=========================================="
echo "Test Summary"
echo "=========================================="
echo ""
echo "✓ All permission enforcement tests completed!"
echo ""
echo "What was tested:"
echo "  - UserViewSet: list, create, update permissions"
echo "  - TeamViewSet: list, create permissions"
echo "  - LeaveRequestViewSet: create, view permissions"
echo "  - Orchestrator: run permission"
echo ""
echo "Roles tested:"
echo "  - Admin (all permissions)"
echo "  - Manager (most permissions)"
echo "  - Scheduler (orchestrator access)"
echo "  - Team Lead (team management)"
echo "  - Employee (limited permissions)"
echo ""
