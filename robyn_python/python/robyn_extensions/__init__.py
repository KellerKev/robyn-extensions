"""
Robyn Extensions - FastAPI-like features for Robyn

Provides validation, OpenAPI docs, rate limiting, and OAuth authentication.
"""

from .decorators import body, query, oauth, openapi_route
from .openapi import OpenAPIGenerator
from .validation import validate_model
from .auth import JWTValidator, oauth_config

# Pydantic v2-compatible models
from .models import (
    BaseModel,
    Field,
    ValidationError as ModelValidationError,
    computed_field,
    field_validator,
    model_validator,
)
from .decorators_v2 import body as body_v2, validated_route, returns

# OpenAPI documentation (FastAPI-style)
from .autodocs import AutoDocs
from .openapi_docs import OpenAPIGenerator as OpenAPIGen, setup_openapi_docs

# Rate limiting (FastAPI-style)
from .ratelimit import (
    rate_limit,
    rate_limit_per_user,
    rate_limit_per_ip,
    rate_limit_global,
    RateLimitConfig,
    strict,
    moderate,
    permissive,
    api_standard,
)

# Authentication (FastAPI-style)
from .easy_auth import (
    setup_auth,
    AuthConfig,
    OIDCProviders,
    require_auth,
    optional_auth,
    require_scope,
    require_any_scope,
    require_all_scopes,
    admin_required,
    read_required,
    write_required,
    delete_required,
)

# REST API Generator (PyDAL-style)
from .restapi import (
    RestAPI,
    CRUDResource,
    QueryParser,
)

# Import Rust-based components
try:
    from robyn_extensions._robyn_extensions import (
        Validator,
        ValidationError,
        RateLimitManager,
    )
except ImportError:
    # Fallback if native module not built
    Validator = None
    ValidationError = None
    RateLimitManager = None

__version__ = "0.1.0"

__all__ = [
    # Original decorators
    "body",
    "query",
    "oauth",
    "openapi_route",
    # Pydantic v2-like models
    "BaseModel",
    "Field",
    "ModelValidationError",
    "body_v2",
    "validated_route",
    "returns",
    "computed_field",
    "field_validator",
    "model_validator",
    # OpenAPI documentation
    "AutoDocs",
    "OpenAPIGen",
    "setup_openapi_docs",
    # Rate limiting
    "rate_limit",
    "rate_limit_per_user",
    "rate_limit_per_ip",
    "rate_limit_global",
    "RateLimitConfig",
    "strict",
    "moderate",
    "permissive",
    "api_standard",
    # Authentication
    "setup_auth",
    "AuthConfig",
    "OIDCProviders",
    "require_auth",
    "optional_auth",
    "require_scope",
    "require_any_scope",
    "require_all_scopes",
    "admin_required",
    "read_required",
    "write_required",
    "delete_required",
    # REST API Generator
    "RestAPI",
    "CRUDResource",
    "QueryParser",
    # Other features
    "OpenAPIGenerator",
    "validate_model",
    "JWTValidator",
    "oauth_config",
    # Rust validators
    "Validator",
    "ValidationError",
    "RateLimitManager",
]
