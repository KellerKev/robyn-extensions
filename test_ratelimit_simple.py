"""
Simple test for rate limiting
"""
import sys
sys.path.insert(0, 'robyn_python/python')

from robyn_extensions._robyn_extensions import RateLimitManager

# Test the Rust rate limiter directly
print("Testing Rust Rate Limiter...")
manager = RateLimitManager()

# Register a limit: 3 requests per 10 seconds
manager.register_limit("test", 3, 10)
print("✅ Registered limit: 3 requests per 10 seconds")

# Test requests
for i in range(5):
    try:
        manager.check("test", "user1")
        print(f"✅ Request {i+1}: Success")
    except RuntimeError as e:
        print(f"❌ Request {i+1}: Rate limited - {e}")

print()
print("Test Summary:")
print("- First 3 requests should succeed")
print("- Requests 4 and 5 should be rate limited")
