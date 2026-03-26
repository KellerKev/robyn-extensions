"""
OpenAPI specification generator for Robyn routes.
"""

import inspect
from typing import Dict, Any, Optional, List
from pydantic import BaseModel


class OpenAPIGenerator:
    """Generate OpenAPI 3.0 specification from decorated routes."""
    
    def __init__(
        self,
        title: str = "API",
        version: str = "1.0.0",
        description: Optional[str] = None
    ):
        self.title = title
        self.version = version
        self.description = description
        self.routes = []
        
    def add_route(
        self,
        path: str,
        method: str,
        handler: callable,
        tags: Optional[List[str]] = None
    ):
        """Register a route for OpenAPI documentation."""
        self.routes.append({
            "path": path,
            "method": method.lower(),
            "handler": handler,
            "tags": tags or []
        })
    
    def _get_model_schema(self, model: type[BaseModel]) -> Dict[str, Any]:
        """Convert Pydantic model to OpenAPI schema."""
        return model.model_json_schema()
    
    def _generate_operation(self, route: Dict) -> Dict[str, Any]:
        """Generate OpenAPI operation object for a route."""
        handler = route["handler"]
        operation = {
            "responses": {
                "200": {"description": "Successful response"}
            }
        }
        
        # Add metadata from decorators
        if hasattr(handler, "_openapi_metadata"):
            metadata = handler._openapi_metadata
            if metadata.get("summary"):
                operation["summary"] = metadata["summary"]
            if metadata.get("description"):
                operation["description"] = metadata["description"]
            if metadata.get("tags"):
                operation["tags"] = metadata["tags"]
            if metadata.get("responses"):
                operation["responses"].update(metadata["responses"])
        
        # Add body schema
        if hasattr(handler, "_body_model"):
            model = handler._body_model
            operation["requestBody"] = {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": self._get_model_schema(model)
                    }
                }
            }
            if hasattr(handler, "_body_description"):
                operation["requestBody"]["description"] = handler._body_description
        
        # Add query parameters
        if hasattr(handler, "_query_model"):
            model = handler._query_model
            schema = self._get_model_schema(model)
            parameters = []
            for name, prop in schema.get("properties", {}).items():
                param = {
                    "name": name,
                    "in": "query",
                    "schema": prop,
                    "required": name in schema.get("required", [])
                }
                parameters.append(param)
            operation["parameters"] = parameters
        
        # Add security if OAuth configured
        if hasattr(handler, "_oauth_config"):
            operation["security"] = [{"bearerAuth": []}]
        
        # Add rate limit info to description
        if hasattr(handler, "_rate_limit"):
            rl = handler._rate_limit
            note = f"\n\nRate limit: {rl['requests']} requests per {rl['per_seconds']} seconds"
            operation["description"] = operation.get("description", "") + note
        
        # Add tags from route
        if route.get("tags"):
            operation.setdefault("tags", []).extend(route["tags"])
        
        return operation
    
    def generate_spec(self) -> Dict[str, Any]:
        """Generate complete OpenAPI specification."""
        spec = {
            "openapi": "3.0.3",
            "info": {
                "title": self.title,
                "version": self.version
            },
            "paths": {}
        }
        
        if self.description:
            spec["info"]["description"] = self.description
        
        # Add security schemes
        has_oauth = any(
            hasattr(r["handler"], "_oauth_config") 
            for r in self.routes
        )
        if has_oauth:
            spec["components"] = {
                "securitySchemes": {
                    "bearerAuth": {
                        "type": "http",
                        "scheme": "bearer",
                        "bearerFormat": "JWT"
                    }
                }
            }
        
        # Generate paths
        for route in self.routes:
            path = route["path"]
            method = route["method"]
            
            if path not in spec["paths"]:
                spec["paths"][path] = {}
            
            spec["paths"][path][method] = self._generate_operation(route)
        
        return spec
    
    def to_json(self) -> str:
        """Generate OpenAPI spec as JSON string."""
        import json
        return json.dumps(self.generate_spec(), indent=2)
    
    def to_yaml(self) -> str:
        """Generate OpenAPI spec as YAML string."""
        try:
            import yaml
            return yaml.dump(self.generate_spec(), sort_keys=False)
        except ImportError:
            raise ImportError("PyYAML required for YAML output: pip install pyyaml")
