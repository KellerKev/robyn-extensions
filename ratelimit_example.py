"""
Easy Rate Limiting Example for Robyn

Demonstrates FastAPI-style rate limiting with Rust performance.
"""
import sys
sys.path.insert(0, 'robyn_python/python')

from robyn import Robyn, Request
from robyn_extensions import (
    rate_limit,
    rate_limit_per_ip,
    rate_limit_per_user,
    rate_limit_global,
    RateLimitConfig,
    strict,
    moderate,
    permissive,
)
import json
import time

app = Robyn(__file__)

# Example 1: Basic rate limiting (10 requests per minute per IP)
@app.get("/api/basic")
@rate_limit(requests=10, per_seconds=60)
def basic_rate_limit(request: Request):
    """10 requests per minute per IP address"""
    return json.dumps({
        "endpoint": "/api/basic",
        "limit": "10 requests per minute",
        "message": "Request successful"
    })


# Example 2: Using preset configurations
@app.get("/api/strict")
@strict()  # 10 requests per minute
def strict_limit(request: Request):
    """Strict rate limit: 10 requests per minute"""
    return json.dumps({
        "endpoint": "/api/strict",
        "preset": "strict",
        "limit": "10 requests per minute"
    })


@app.get("/api/moderate")
@moderate()  # 60 requests per minute
def moderate_limit(request: Request):
    """Moderate rate limit: 60 requests per minute"""
    return json.dumps({
        "endpoint": "/api/moderate",
        "preset": "moderate",
        "limit": "60 requests per minute"
    })


@app.get("/api/permissive")
@permissive()  # 100 requests per minute
def permissive_limit(request: Request):
    """Permissive rate limit: 100 requests per minute"""
    return json.dumps({
        "endpoint": "/api/permissive",
        "preset": "permissive",
        "limit": "100 requests per minute"
    })


# Example 3: Per-user rate limiting
@app.get("/api/profile")
@rate_limit_per_user(requests=50, per_seconds=60)
def user_profile(request: Request):
    """50 requests per minute per user"""
    user_id = request.headers.get("user_id", "anonymous")
    return json.dumps({
        "endpoint": "/api/profile",
        "user_id": user_id,
        "limit": "50 requests per minute per user",
        "message": "User profile retrieved"
    })


# Example 4: Explicit per-IP rate limiting
@app.get("/api/public")
@rate_limit_per_ip(requests=30, per_seconds=60)
def public_endpoint(request: Request):
    """30 requests per minute per IP"""
    return json.dumps({
        "endpoint": "/api/public",
        "limit": "30 requests per minute per IP",
        "message": "Public data"
    })


# Example 5: Global rate limiting (shared across all clients)
@app.get("/api/expensive")
@rate_limit_global(requests=100, per_seconds=60)
def expensive_operation(request: Request):
    """100 total requests per minute (global)"""
    time.sleep(0.1)  # Simulate expensive operation
    return json.dumps({
        "endpoint": "/api/expensive",
        "limit": "100 requests per minute (global)",
        "message": "Expensive operation completed"
    })


# Example 6: Custom rate limit with custom key function
@app.get("/api/users/:user_id/data")
@rate_limit(
    requests=20,
    per_seconds=60,
    key_func=lambda req: req.path_params.get("user_id", "unknown")
)
def user_data(request: Request):
    """20 requests per minute per user_id from path"""
    user_id = request.path_params.get("user_id", "unknown")
    return json.dumps({
        "endpoint": "/api/users/{user_id}/data",
        "user_id": user_id,
        "limit": "20 requests per minute per user",
        "data": f"Data for user {user_id}"
    })


# Example 7: Very strict rate limit (easy to test)
@app.get("/api/test")
@rate_limit(requests=3, per_seconds=10)
def test_rate_limit(request: Request):
    """3 requests per 10 seconds - easy to test!"""
    return json.dumps({
        "endpoint": "/api/test",
        "limit": "3 requests per 10 seconds",
        "message": "Request successful",
        "tip": "Try hitting this endpoint 4 times quickly!"
    })


# Example 8: Different limits for different HTTP methods
@app.get("/api/resource")
@rate_limit(requests=100, per_seconds=60)
def get_resource(request: Request):
    """100 GET requests per minute"""
    return json.dumps({"method": "GET", "limit": "100/min"})


@app.post("/api/resource")
@rate_limit(requests=20, per_seconds=60)
def create_resource(request: Request):
    """20 POST requests per minute"""
    return json.dumps({"method": "POST", "limit": "20/min"})


# Example 9: Using RateLimitConfig for custom configurations
@app.get("/api/custom")
@rate_limit(**RateLimitConfig.custom(requests=15, per_seconds=30))
def custom_limit(request: Request):
    """15 requests per 30 seconds"""
    return json.dumps({
        "endpoint": "/api/custom",
        "limit": "15 requests per 30 seconds"
    })


# Home page with documentation
@app.get("/")
def index(request: Request):
    """API documentation"""
    return json.dumps({
        "title": "Rate Limiting Demo for Robyn",
        "description": "FastAPI-style rate limiting with Rust performance",
        "endpoints": {
            "/api/basic": "Basic rate limit (10/min)",
            "/api/strict": "Strict preset (10/min)",
            "/api/moderate": "Moderate preset (60/min)",
            "/api/permissive": "Permissive preset (100/min)",
            "/api/profile": "Per-user limit (50/min) - add 'user_id' header",
            "/api/public": "Per-IP limit (30/min)",
            "/api/expensive": "Global limit (100/min total)",
            "/api/users/:user_id/data": "Per-user limit from path (20/min)",
            "/api/test": "Test limit (3 per 10 seconds) - EASY TO TEST!",
            "/api/resource": "GET: 100/min, POST: 20/min",
            "/api/custom": "Custom limit (15 per 30 seconds)"
        },
        "testing": {
            "easy_test": "curl http://localhost:8082/api/test (4 times quickly)",
            "per_user": "curl -H 'user_id: alice' http://localhost:8082/api/profile",
            "rate_limited_response": {
                "status": 429,
                "body": {
                    "error": "Rate limit exceeded",
                    "retry_after": 60
                },
                "headers": {
                    "Retry-After": "60"
                }
            }
        },
        "features": [
            "🚀 Rust-based rate limiting (high performance)",
            "⚡ Zero-copy concurrent operations",
            "🎯 Multiple rate limit strategies",
            "🔑 Flexible key extraction",
            "📊 Automatic 429 responses",
            "⏱️ Retry-After headers"
        ]
    })


if __name__ == "__main__":
    print("🚀 Starting Robyn with Rust-based Rate Limiting...")
    print("📚 Endpoints:")
    print("   - Home:    http://localhost:8082/")
    print("   - Test:    http://localhost:8082/api/test (3 per 10 sec)")
    print("   - Basic:   http://localhost:8082/api/basic (10 per min)")
    print("   - Profile: http://localhost:8082/api/profile (50 per min)")
    print()
    print("💡 Easy test:")
    print("   curl http://localhost:8082/api/test (run 4 times quickly)")
    print()
    app.start(host="0.0.0.0", port=8082)
