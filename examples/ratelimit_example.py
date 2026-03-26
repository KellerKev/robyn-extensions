"""
Rate limiting example — configurable per-IP, per-user, and global limits.

Demonstrates:
  - Basic rate limiting with @rate_limit
  - Presets (strict, moderate, permissive, api_standard)
  - Per-user and global rate limiting
  - Custom key functions
"""

from robyn import Robyn, Request
from robyn_extensions import (
    rate_limit, rate_limit_per_user, rate_limit_per_ip, rate_limit_global,
    RateLimitConfig, strict, moderate, permissive, api_standard,
)

app = Robyn(__file__)


# === Basic Rate Limiting ===

@app.get("/api/data")
@rate_limit(requests=100, per_seconds=60)
def get_data(request: Request):
    '''100 requests per minute per IP address'''
    return {"data": "..."}


# === Presets ===

@app.post("/auth/login")
@strict()
def login(request: Request):
    '''10 req/min — for sensitive endpoints like login'''
    return {"token": "..."}


@app.get("/api/items")
@moderate()
def list_items(request: Request):
    '''60 req/min — standard API endpoint'''
    return {"items": []}


@app.get("/api/search")
@permissive()
def search(request: Request):
    '''100 req/min — read-heavy endpoints'''
    return {"results": []}


@app.get("/api/export")
@api_standard()
def bulk_export(request: Request):
    '''1000 req/hour — bulk operations'''
    return {"export_url": "..."}


# === Per-User Rate Limiting ===

@app.get("/api/me")
@rate_limit_per_user(requests=50, per_seconds=60, user_key="user_id")
def my_profile(request: Request):
    '''50 req/min per user (extracted from user_id header)'''
    return {"profile": "..."}


# === Global Rate Limiting ===

@app.get("/api/health")
@rate_limit_global(requests=1000, per_seconds=60)
def health(request: Request):
    '''1000 req/min shared across ALL clients'''
    return {"status": "ok"}


# === Custom Key Function ===

@app.get("/api/org/:org_id/data")
@rate_limit(
    requests=200,
    per_seconds=60,
    key_func=lambda r: r.path_params.get("org_id", "unknown")
)
def org_data(request: Request):
    '''200 req/min per organization'''
    return {"org_data": "..."}


# === Using RateLimitConfig for Dynamic Configuration ===

@app.get("/api/premium")
@rate_limit(**RateLimitConfig.custom(requests=500, per_seconds=60))
def premium_endpoint(request: Request):
    '''Custom limit: 500 req/min'''
    return {"premium": True}


if __name__ == "__main__":
    app.start(port=8080)
