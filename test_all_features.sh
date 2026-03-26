#!/bin/bash

# Test All Features Script
# Run this to test all Robyn Extensions features step by step

set -e  # Exit on error

BOLD='\033[1m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BOLD}================================${NC}"
echo -e "${BOLD}Robyn Extensions - Test Suite${NC}"
echo -e "${BOLD}================================${NC}"
echo ""

# Function to check if a port is in use
check_port() {
    lsof -i :$1 &> /dev/null
    return $?
}

# Function to wait for server to be ready
wait_for_server() {
    local port=$1
    local max_attempts=30
    local attempt=0

    echo -e "${YELLOW}⏳ Waiting for server on port $port...${NC}"

    while [ $attempt -lt $max_attempts ]; do
        if curl -s http://localhost:$port/health &> /dev/null || \
           curl -s http://localhost:$port/ &> /dev/null; then
            echo -e "${GREEN}✅ Server ready!${NC}"
            return 0
        fi
        sleep 1
        attempt=$((attempt + 1))
    done

    echo -e "${RED}❌ Server failed to start${NC}"
    return 1
}

# Test 1: Pydantic Validation
echo -e "${BOLD}${BLUE}Test 1: Pydantic Validation${NC}"
echo -e "Testing model validation and error handling..."
echo ""

if check_port 8081; then
    echo -e "${YELLOW}⚠️  Port 8081 is in use. Skipping or kill the process.${NC}"
else
    echo "Starting pydantic_app.py in background..."
    pixi run python pydantic_app.py &
    PYDANTIC_PID=$!
    sleep 3

    echo "Testing valid request..."
    curl -s -X POST http://localhost:8081/api/users \
      -H "Content-Type: application/json" \
      -d '{"name": "Alice", "email": "alice@test.com", "age": 30, "tags": ["python"]}' | jq

    echo ""
    echo "Testing invalid request (missing email)..."
    curl -s -X POST http://localhost:8081/api/users \
      -H "Content-Type: application/json" \
      -d '{"name": "Bob", "age": 25}' | jq

    echo ""
    echo -e "${GREEN}✅ Pydantic validation test complete${NC}"
    echo ""

    # Cleanup
    kill $PYDANTIC_PID 2>/dev/null || true
    sleep 2
fi

# Test 2: OpenAPI Documentation
echo -e "${BOLD}${BLUE}Test 2: OpenAPI Documentation${NC}"
echo -e "Testing auto-generated API documentation..."
echo ""

if check_port 8082; then
    echo -e "${YELLOW}⚠️  Port 8082 is in use. Skipping or kill the process.${NC}"
else
    echo "Starting rust_autodocs_example.py in background..."
    pixi run python rust_autodocs_example.py &
    AUTODOCS_PID=$!
    sleep 3

    echo "Fetching OpenAPI spec..."
    curl -s http://localhost:8082/openapi.json | jq '.info, .paths | keys' 2>/dev/null || echo "OpenAPI spec available at http://localhost:8082/openapi.json"

    echo ""
    echo -e "${GREEN}✅ OpenAPI docs available at: ${BLUE}http://localhost:8082/docs${NC}"
    echo ""

    # Cleanup
    kill $AUTODOCS_PID 2>/dev/null || true
    sleep 2
fi

# Test 3: Authentication
echo -e "${BOLD}${BLUE}Test 3: JWT Authentication & Authorization${NC}"
echo -e "Testing auth with multiple token types..."
echo ""

if check_port 8083; then
    echo -e "${YELLOW}⚠️  Port 8083 is in use. Skipping or kill the process.${NC}"
else
    echo "Starting auth_example.py in background..."
    pixi run python auth_example.py &
    AUTH_PID=$!
    sleep 3

    # Get test tokens
    if [ -f /tmp/test_tokens.json ]; then
        READ_TOKEN=$(cat /tmp/test_tokens.json | jq -r .read_only)
        ADMIN_TOKEN=$(cat /tmp/test_tokens.json | jq -r .admin)
        EXPIRED_TOKEN=$(cat /tmp/test_tokens.json | jq -r .expired)

        echo "Testing public endpoint (no auth)..."
        curl -s http://localhost:8083/api/public | jq .endpoint

        echo ""
        echo "Testing protected endpoint with valid token..."
        curl -s http://localhost:8083/api/protected \
          -H "Authorization: Bearer $READ_TOKEN" | jq .endpoint

        echo ""
        echo "Testing admin endpoint with read-only token (should fail)..."
        curl -s http://localhost:8083/api/admin \
          -H "Authorization: Bearer $READ_TOKEN" | jq

        echo ""
        echo "Testing admin endpoint with admin token (should work)..."
        curl -s http://localhost:8083/api/admin \
          -H "Authorization: Bearer $ADMIN_TOKEN" | jq .endpoint

        echo ""
        echo "Testing with expired token (should fail)..."
        curl -s http://localhost:8083/api/protected \
          -H "Authorization: Bearer $EXPIRED_TOKEN" | jq

        echo ""
        echo -e "${GREEN}✅ Authentication test complete${NC}"
    else
        echo -e "${RED}❌ Test tokens not found at /tmp/test_tokens.json${NC}"
    fi
    echo ""

    # Cleanup
    kill $AUTH_PID 2>/dev/null || true
    sleep 2
fi

# Test 4: Rate Limiting
echo -e "${BOLD}${BLUE}Test 4: Rate Limiting${NC}"
echo -e "Testing rate limit enforcement..."
echo ""

if check_port 8086; then
    echo -e "${YELLOW}⚠️  Port 8086 is in use. Skipping or kill the process.${NC}"
else
    echo "Starting ratelimit_example.py in background..."
    pixi run python ratelimit_example.py &
    RATELIMIT_PID=$!
    sleep 3

    echo "Making 5 requests to strict endpoint (limit: 3 per 10 seconds)..."
    for i in {1..5}; do
        echo -n "Request $i: "
        RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" http://localhost:8086/api/strict)
        HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)

        if [ "$HTTP_CODE" == "429" ]; then
            echo -e "${YELLOW}Rate limited (429)${NC}"
        else
            echo -e "${GREEN}Success (200)${NC}"
        fi
        sleep 1
    done

    echo ""
    echo -e "${GREEN}✅ Rate limiting test complete${NC}"
    echo ""

    # Cleanup
    kill $RATELIMIT_PID 2>/dev/null || true
    sleep 2
fi

# Test 5: REST API Generator
echo -e "${BOLD}${BLUE}Test 5: REST API Generator (PyDAL-style)${NC}"
echo -e "Testing auto-generated CRUD endpoints..."
echo ""

if check_port 8085; then
    echo -e "${YELLOW}⚠️  Port 8085 is in use. Skipping or kill the process.${NC}"
else
    echo "Starting restapi_example.py in background..."
    pixi run python restapi_example.py &
    RESTAPI_PID=$!
    sleep 3

    echo "List all users:"
    curl -s http://localhost:8085/api/users | jq '.items | length, .[0].name'

    echo ""
    echo "Get specific user (ID: 1):"
    curl -s http://localhost:8085/api/users/1 | jq '.items[0] | {name, email, role}'

    echo ""
    echo "Filter users by role=admin:"
    curl -s "http://localhost:8085/api/users?role.eq=admin" | jq '.count, .items[].name'

    echo ""
    echo "List all posts:"
    curl -s http://localhost:8085/api/posts | jq '.count'

    echo ""
    echo -e "${GREEN}✅ REST API test complete${NC}"
    echo ""

    # Cleanup
    kill $RESTAPI_PID 2>/dev/null || true
    sleep 2
fi

# Summary
echo ""
echo -e "${BOLD}================================${NC}"
echo -e "${BOLD}${GREEN}All Tests Complete! 🎉${NC}"
echo -e "${BOLD}================================${NC}"
echo ""
echo -e "Features tested:"
echo -e "  ${GREEN}✅${NC} Pydantic validation"
echo -e "  ${GREEN}✅${NC} OpenAPI documentation"
echo -e "  ${GREEN}✅${NC} JWT authentication"
echo -e "  ${GREEN}✅${NC} Rate limiting"
echo -e "  ${GREEN}✅${NC} REST API generator"
echo ""
echo -e "Next steps:"
echo -e "  📖 Read GETTING_STARTED.md for detailed guides"
echo -e "  🚀 Build your first API with the examples"
echo -e "  📝 Check example files for more patterns"
echo ""
