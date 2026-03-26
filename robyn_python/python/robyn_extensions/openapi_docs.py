"""
FastAPI-style OpenAPI documentation for Robyn
Automatic Swagger UI integration with route introspection
"""

from typing import Dict, Any, List, Optional, Type, get_type_hints, get_origin
from .models import BaseModel
import inspect
import json


class OpenAPIGenerator:
    """
    Generate OpenAPI documentation automatically from Robyn routes

    Usage:
        from robyn import Robyn
        from robyn_extensions import OpenAPIGenerator, BaseModel, body_v2

        app = Robyn(__file__)
        docs = OpenAPIGenerator(
            title="My API",
            version="1.0.0",
            description="API with automatic OpenAPI docs"
        )

        @app.post("/users")
        @body_v2(UserCreate)
        @docs.route(
            summary="Create a new user",
            description="Creates a user with automatic validation",
            tags=["users"]
        )
        def create_user(request, user: UserCreate):
            return user.model_dump()

        # Add documentation endpoints
        docs.setup(app)

        # Now you have:
        # - GET /docs - Swagger UI
        # - GET /openapi.json - OpenAPI schema
    """

    def __init__(
        self,
        title: str = "API",
        version: str = "1.0.0",
        description: str = "",
        contact: Optional[Dict[str, str]] = None,
        license_info: Optional[Dict[str, str]] = None,
    ):
        self.title = title
        self.version = version
        self.description = description
        self.contact = contact or {}
        self.license_info = license_info or {}
        self.routes: List[Dict[str, Any]] = []
        self.schemas: Dict[str, Any] = {}

    def route(
        self,
        *,
        summary: str = "",
        description: str = "",
        tags: Optional[List[str]] = None,
        response_model: Optional[Type[BaseModel]] = None,
        responses: Optional[Dict[int, Dict[str, Any]]] = None,
    ):
        """
        Decorator to document a route

        Args:
            summary: Short summary of the endpoint
            description: Detailed description
            tags: List of tags for grouping
            response_model: Expected response model
            responses: Additional response schemas
        """
        def decorator(func):
            # Extract information from function
            route_info = {
                'func': func,
                'summary': summary or func.__name__.replace('_', ' ').title(),
                'description': description or func.__doc__ or "",
                'tags': tags or [],
                'response_model': response_model,
                'responses': responses or {},
            }

            # Try to extract request/response models from type hints
            hints = get_type_hints(func) if hasattr(func, '__annotations__') else {}
            sig = inspect.signature(func)

            # Find BaseModel parameters (request body)
            for param_name, param in sig.parameters.items():
                if param_name == 'request':
                    continue
                param_type = hints.get(param_name)
                if param_type and inspect.isclass(param_type) and issubclass(param_type, BaseModel):
                    route_info['request_model'] = param_type

            # Check return type
            return_type = hints.get('return')
            if return_type and inspect.isclass(return_type) and issubclass(return_type, BaseModel):
                route_info['response_model'] = return_type

            self.routes.append(route_info)

            # Mark function with route info for later extraction
            func._openapi_info = route_info

            return func
        return decorator

    def generate_openapi_spec(self) -> Dict[str, Any]:
        """
        Generate complete OpenAPI 3.0 specification
        """
        spec = {
            "openapi": "3.0.0",
            "info": {
                "title": self.title,
                "version": self.version,
                "description": self.description,
            },
            "paths": {},
            "components": {
                "schemas": {}
            }
        }

        if self.contact:
            spec["info"]["contact"] = self.contact
        if self.license_info:
            spec["info"]["license"] = self.license_info

        # Process each route
        for route_info in self.routes:
            path = route_info.get('path', '/')
            method = route_info.get('method', 'get').lower()

            if path not in spec["paths"]:
                spec["paths"][path] = {}

            # Build operation
            operation = {
                "summary": route_info['summary'],
                "description": route_info['description'],
                "tags": route_info['tags'],
                "responses": {}
            }

            # Add request body if there's a request model
            if 'request_model' in route_info:
                model = route_info['request_model']
                schema = model.model_json_schema()
                model_name = model.__name__

                # Add to components
                if model_name not in spec["components"]["schemas"]:
                    spec["components"]["schemas"][model_name] = schema
                    # Also add nested schemas
                    if "$defs" in schema:
                        spec["components"]["schemas"].update(schema["$defs"])
                        del schema["$defs"]

                operation["requestBody"] = {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": f"#/components/schemas/{model_name}"}
                        }
                    }
                }

            # Add response schema
            response_model = route_info.get('response_model')
            if response_model:
                schema = response_model.model_json_schema()
                model_name = response_model.__name__

                if model_name not in spec["components"]["schemas"]:
                    spec["components"]["schemas"][model_name] = schema
                    if "$defs" in schema:
                        spec["components"]["schemas"].update(schema["$defs"])
                        del schema["$defs"]

                operation["responses"]["200"] = {
                    "description": "Successful response",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": f"#/components/schemas/{model_name}"}
                        }
                    }
                }
            else:
                operation["responses"]["200"] = {
                    "description": "Successful response"
                }

            # Add validation error response
            operation["responses"]["422"] = {
                "description": "Validation Error",
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "error": {"type": "string"},
                                "detail": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "field": {"type": "string"},
                                            "message": {"type": "string"}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }

            spec["paths"][path][method] = operation

        return spec

    def extract_routes_from_app(self, app):
        """
        Extract route information from Robyn app
        This is called during setup()
        """
        # Try to access Robyn's internal route registry
        # Note: This is somewhat hacky and depends on Robyn's internal structure
        if hasattr(app, '_routes'):
            for route in app._routes:
                # Extract path and method
                path = getattr(route, 'path', '/')
                method = getattr(route, 'method', 'GET')
                handler = getattr(route, 'handler', None)

                if handler and hasattr(handler, '_openapi_info'):
                    info = handler._openapi_info
                    info['path'] = path
                    info['method'] = method

    def setup(self, app):
        """
        Add OpenAPI documentation endpoints to Robyn app

        Adds:
        - GET /openapi.json - OpenAPI spec
        - GET /docs - Swagger UI
        - GET /redoc - ReDoc UI
        """
        from robyn import Request

        # Extract routes that were decorated
        self.extract_routes_from_app(app)

        @app.get("/openapi.json")
        def get_openapi_spec(request: Request):
            """Get OpenAPI specification"""
            return self.generate_openapi_spec()

        @app.get("/docs")
        def get_swagger_ui(request: Request):
            """Swagger UI documentation"""
            html = self._generate_swagger_ui_html()
            return html

        @app.get("/redoc")
        def get_redoc_ui(request: Request):
            """ReDoc UI documentation"""
            html = self._generate_redoc_html()
            return html

        print(f"📚 OpenAPI docs available at:")
        print(f"   - Swagger UI: http://localhost:{getattr(app, 'port', 8080)}/docs")
        print(f"   - ReDoc:      http://localhost:{getattr(app, 'port', 8080)}/redoc")
        print(f"   - OpenAPI:    http://localhost:{getattr(app, 'port', 8080)}/openapi.json")

    def _generate_swagger_ui_html(self) -> str:
        """Generate Swagger UI HTML"""
        return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self.title} - Swagger UI</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.10.0/swagger-ui.css">
    <style>
        body {{
            margin: 0;
            padding: 0;
        }}
    </style>
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.10.0/swagger-ui-bundle.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.10.0/swagger-ui-standalone-preset.js"></script>
    <script>
        window.onload = function() {{
            const ui = SwaggerUIBundle({{
                url: '/openapi.json',
                dom_id: '#swagger-ui',
                deepLinking: true,
                presets: [
                    SwaggerUIBundle.presets.apis,
                    SwaggerUIStandalonePreset
                ],
                plugins: [
                    SwaggerUIBundle.plugins.DownloadUrl
                ],
                layout: "StandaloneLayout"
            }});
            window.ui = ui;
        }};
    </script>
</body>
</html>
"""

    def _generate_redoc_html(self) -> str:
        """Generate ReDoc HTML"""
        return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self.title} - ReDoc</title>
    <style>
        body {{
            margin: 0;
            padding: 0;
        }}
    </style>
</head>
<body>
    <redoc spec-url='/openapi.json'></redoc>
    <script src="https://cdn.jsdelivr.net/npm/redoc@latest/bundles/redoc.standalone.js"></script>
</body>
</html>
"""


# Convenience function for quick setup
def setup_openapi_docs(
    app,
    title: str = "API",
    version: str = "1.0.0",
    description: str = "",
) -> OpenAPIGenerator:
    """
    Quick setup for OpenAPI documentation

    Usage:
        from robyn import Robyn
        from robyn_extensions import setup_openapi_docs

        app = Robyn(__file__)
        docs = setup_openapi_docs(app, title="My API", version="1.0.0")

        @app.get("/users")
        @docs.route(summary="List users", tags=["users"])
        def list_users(request):
            return {"users": []}
    """
    docs = OpenAPIGenerator(title=title, version=version, description=description)
    docs.setup(app)
    return docs
