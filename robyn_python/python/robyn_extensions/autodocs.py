"""
Automatic OpenAPI documentation for Robyn (FastAPI-style)
Works by introspecting routes and decorated functions
"""

from typing import Dict, Any, List, Optional, Type, get_type_hints
from .models import BaseModel
import inspect


class AutoDocs:
    """
    Automatic OpenAPI documentation generator for Robyn

    This is the easiest way to add Swagger UI to your Robyn app:

    Usage:
        from robyn import Robyn
        from robyn_extensions import AutoDocs, BaseModel, body_v2

        app = Robyn(__file__)

        # Enable automatic documentation
        docs = AutoDocs(
            app,
            title="My API",
            version="1.0.0",
            description="API with automatic docs"
        )

        class User(BaseModel):
            username: str
            email: str

        @app.post("/users")
        @body_v2(User)
        def create_user(request, user: User):
            '''Create a new user'''
            return user.model_dump()

        # That's it! Now visit:
        # http://localhost:8080/docs - Swagger UI
        # http://localhost:8080/openapi.json - OpenAPI spec
    """

    def __init__(
        self,
        app,
        title: str = "API",
        version: str = "1.0.0",
        description: str = "",
        docs_url: str = "/docs",
        openapi_url: str = "/openapi.json",
        redoc_url: str = "/redoc",
    ):
        self.app = app
        self.title = title
        self.version = version
        self.description = description
        self.docs_url = docs_url
        self.openapi_url = openapi_url
        self.redoc_url = redoc_url

        # Storage for route metadata
        self.route_metadata: Dict[str, Dict[str, Any]] = {}

        # Automatically setup documentation endpoints
        self._setup_docs_endpoints()

    def _setup_docs_endpoints(self):
        """Setup /docs, /openapi.json, and /redoc endpoints"""
        from robyn import Request

        @self.app.get(self.openapi_url)
        def openapi_spec(request: Request):
            """Get OpenAPI specification"""
            return self._generate_openapi_spec()

        @self.app.get(self.docs_url)
        def swagger_ui(request: Request):
            """Swagger UI documentation"""
            return self._swagger_ui_html()

        @self.app.get(self.redoc_url)
        def redoc_ui(request: Request):
            """ReDoc documentation"""
            return self._redoc_html()

    def _generate_openapi_spec(self) -> Dict[str, Any]:
        """Generate OpenAPI 3.0 specification by introspecting the app"""
        spec = {
            "openapi": "3.0.0",
            "info": {
                "title": self.title,
                "version": self.version,
                "description": self.description,
            },
            "paths": {},
            "components": {"schemas": {}}
        }

        # Try to extract routes from Robyn app
        routes = self._extract_routes()

        for route in routes:
            path = route['path']
            method = route['method'].lower()
            handler = route['handler']

            if path not in spec["paths"]:
                spec["paths"][path] = {}

            # Build operation
            operation = self._build_operation(handler, route)
            spec["paths"][path][method] = operation

            # Collect schemas
            schemas = operation.pop('_schemas', {})
            spec["components"]["schemas"].update(schemas)

        return spec

    def _extract_routes(self) -> List[Dict[str, Any]]:
        """Extract route information from Robyn app"""
        routes = []

        # Robyn stores routes in different ways depending on version
        # Try multiple approaches

        # Approach 1: Check for router attribute
        if hasattr(self.app, 'router'):
            router = self.app.router
            if hasattr(router, 'routes'):
                for route in router.routes:
                    routes.append({
                        'path': getattr(route, 'endpoint', '/'),
                        'method': getattr(route, 'methods', ['GET'])[0] if hasattr(route, 'methods') else 'GET',
                        'handler': getattr(route, 'handler', None)
                    })

        # Approach 2: Check internal route storage
        if hasattr(self.app, '_routes'):
            for route_key, handler in self.app._routes.items():
                if isinstance(route_key, tuple):
                    method, path = route_key
                    routes.append({
                        'path': path,
                        'method': method,
                        'handler': handler
                    })

        # Approach 3: Scan for decorated methods
        # This works by scanning all methods that might have been decorated
        for attr_name in dir(self.app):
            attr = getattr(self.app, attr_name, None)
            if callable(attr) and hasattr(attr, '__wrapped__'):
                # This might be a route handler
                pass

        return routes

    def _build_operation(self, handler, route: Dict[str, Any]) -> Dict[str, Any]:
        """Build OpenAPI operation object for a route handler"""
        operation = {
            "summary": self._get_summary(handler),
            "description": self._get_description(handler),
            "responses": {
                "200": {"description": "Successful response"},
                "422": {
                    "description": "Validation Error",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "error": {"type": "string"},
                                    "detail": {"type": "array"}
                                }
                            }
                        }
                    }
                }
            },
            "_schemas": {}
        }

        # Extract request/response models from type hints
        try:
            hints = get_type_hints(handler)
            sig = inspect.signature(handler)

            # Find request body model
            for param_name, param in sig.parameters.items():
                if param_name == 'request':
                    continue
                param_type = hints.get(param_name)
                if param_type and self._is_base_model(param_type):
                    # Add request body
                    model_name = param_type.__name__
                    schema = param_type.model_json_schema()

                    operation["_schemas"][model_name] = schema
                    if "$defs" in schema:
                        operation["_schemas"].update(schema["$defs"])
                        del schema["$defs"]

                    operation["requestBody"] = {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {"$ref": f"#/components/schemas/{model_name}"}
                            }
                        }
                    }

            # Check return type
            return_type = hints.get('return')
            if return_type and self._is_base_model(return_type):
                model_name = return_type.__name__
                schema = return_type.model_json_schema()

                operation["_schemas"][model_name] = schema
                if "$defs" in schema:
                    operation["_schemas"].update(schema["$defs"])
                    del schema["$defs"]

                operation["responses"]["200"] = {
                    "description": "Successful response",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": f"#/components/schemas/{model_name}"}
                        }
                    }
                }
        except Exception as e:
            # If introspection fails, just use default
            pass

        return operation

    def _is_base_model(self, type_hint) -> bool:
        """Check if a type hint is a BaseModel subclass"""
        try:
            return inspect.isclass(type_hint) and issubclass(type_hint, BaseModel)
        except:
            return False

    def _get_summary(self, handler) -> str:
        """Get summary from handler"""
        if hasattr(handler, '__name__'):
            return handler.__name__.replace('_', ' ').title()
        return "Endpoint"

    def _get_description(self, handler) -> str:
        """Get description from handler docstring"""
        doc = inspect.getdoc(handler)
        return doc or ""

    def _swagger_ui_html(self) -> str:
        """Generate Swagger UI HTML"""
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self.title} - Swagger UI</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.10.0/swagger-ui.css">
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.10.0/swagger-ui-bundle.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.10.0/swagger-ui-standalone-preset.js"></script>
    <script>
        window.onload = function() {{
            SwaggerUIBundle({{
                url: '{self.openapi_url}',
                dom_id: '#swagger-ui',
                deepLinking: true,
                presets: [
                    SwaggerUIBundle.presets.apis,
                    SwaggerUIStandalonePreset
                ],
                layout: "StandaloneLayout"
            }});
        }};
    </script>
</body>
</html>"""

    def _redoc_html(self) -> str:
        """Generate ReDoc HTML"""
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self.title} - ReDoc</title>
</head>
<body>
    <redoc spec-url='{self.openapi_url}'></redoc>
    <script src="https://cdn.jsdelivr.net/npm/redoc@latest/bundles/redoc.standalone.js"></script>
</body>
</html>"""
