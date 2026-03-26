# Installation Guide

## Prerequisites

- Rust 1.70+ ([rustup.rs](https://rustup.rs))
- Python 3.8+
- Robyn framework

## Quick Install

### From source

```bash
# Clone the repository
git clone https://github.com/sparckles/robyn-extensions
cd robyn-extensions

# Build and install Python package
cd robyn_python
pip install maturin
maturin develop --release

# Or build wheel
maturin build --release
pip install target/wheels/*.whl
```

### Using pip (once published)

```bash
pip install robyn-extensions
```

## Development Setup

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
cargo test --workspace
pytest robyn_python/tests/

# Format code
cargo fmt --all
black robyn_python/python/

# Lint
cargo clippy --workspace -- -D warnings
ruff check robyn_python/python/
```

## Building Individual Components

```bash
# Build only validation
cargo build -p robyn_validation --release

# Build only rate limiting
cargo build -p robyn_ratelimit --release

# Build only auth
cargo build -p robyn_auth --release

# Build only OpenAPI
cargo build -p robyn_openapi --release
```

## Configuration

### OAuth/JWT

Set in your Robyn app:

```python
app.config.oauth.jwks_url = "https://auth.example.com/.well-known/jwks.json"
# OR
app.config.oauth.public_key = "-----BEGIN PUBLIC KEY-----\n..."

app.config.oauth.audience = "your-api"
app.config.oauth.issuer = "https://auth.example.com/"
```

### Rate Limiting

Configured per decorator:

```python
@rate_limit(requests=100, per_seconds=60)
def handler(request):
    pass
```

## Troubleshooting

### Rust module not found

Ensure maturin build completed successfully:
```bash
cd robyn_python
maturin develop --release
```

### JWT validation failing

Verify JWKS URL is accessible and returns valid JSON:
```bash
curl https://your-auth-provider.com/.well-known/jwks.json
```

### Rate limiting not working

Check that the Rust extension is properly installed:
```python
from robyn_extensions import RateLimitManager
print(RateLimitManager)
```
