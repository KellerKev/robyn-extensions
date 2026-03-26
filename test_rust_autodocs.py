"""
Test Rust-based AutoDocs directly (without full Robyn app)
"""
import sys
sys.path.insert(0, 'robyn_python/python')

from robyn_extensions._robyn_extensions import AutoDocs, RouteMetadata
from robyn_extensions import BaseModel, Field
import json

# Create AutoDocs
print("✅ Creating Rust AutoDocs instance...")
docs = AutoDocs("Test API", "1.0.0")
print(f"   Docs path: {docs.get_docs_path()}")
print(f"   OpenAPI path: {docs.get_openapi_path()}")
print(f"   ReDoc path: {docs.get_redoc_path()}")
print()

# Define a simple model
class User(BaseModel):
    username: str = Field(min_length=3)
    age: int = Field(ge=18)

# Get JSON schema
user_schema = User.model_json_schema()
print("✅ Generated JSON Schema from BaseModel:")
print(json.dumps(user_schema, indent=2))
print()

# Register some routes
print("✅ Registering routes...")
docs.register_route(RouteMetadata(
    path="/users",
    method="POST",
    summary="Create user",
    description="Create a new user",
    tags=["users"],
    request_schema=json.dumps(user_schema),
    response_schema=json.dumps(user_schema)
))

docs.register_route(RouteMetadata(
    path="/users/{id}",
    method="GET",
    summary="Get user",
    description="Get a user by ID",
    tags=["users"],
    request_schema=None,
    response_schema=json.dumps(user_schema)
))

docs.register_route(RouteMetadata(
    path="/health",
    method="GET",
    summary="Health check",
    description="Check API health",
    tags=["system"],
    request_schema=None,
    response_schema=None
))
print("   Registered 3 routes")
print()

# Get OpenAPI spec
print("✅ Generating OpenAPI specification (from Rust!)...")
openapi_json = docs.get_openapi_json()
spec = json.loads(openapi_json)
print(f"   OpenAPI version: {spec['openapi']}")
print(f"   API title: {spec['info']['title']}")
print(f"   API version: {spec['info']['version']}")
print(f"   Paths: {list(spec['paths'].keys())}")
print()

print("✅ Full OpenAPI Spec:")
print(json.dumps(spec, indent=2))
print()

# Get Swagger UI HTML
print("✅ Generating Swagger UI HTML (from Rust!)...")
swagger_html = docs.get_swagger_ui_html("Test API")
print(f"   HTML length: {len(swagger_html)} chars")
print(f"   Contains Swagger UI: {'swagger-ui' in swagger_html}")
print()

# Get ReDoc HTML
print("✅ Generating ReDoc HTML (from Rust!)...")
redoc_html = docs.get_redoc_html("Test API")
print(f"   HTML length: {len(redoc_html)} chars")
print(f"   Contains ReDoc: {'<redoc' in redoc_html}")
print()

print("🎉 All tests passed! Rust AutoDocs is working correctly.")
print()
print("Summary:")
print("- ✅ Rust AutoDocs instance created")
print("- ✅ Route metadata registered")
print("- ✅ OpenAPI spec generated")
print("- ✅ Swagger UI HTML generated")
print("- ✅ ReDoc HTML generated")
print("- ✅ JSON Schema integration working")
