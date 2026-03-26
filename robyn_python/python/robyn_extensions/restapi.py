"""
REST API Generator for Robyn - PyDAL-inspired

Auto-generates CRUD endpoints from Pydantic models with filtering, pagination,
and policy-based access control. ORM-agnostic design.

Usage:
    from robyn_extensions import RestAPI, CRUDResource

    # Define your model
    class User(BaseModel):
        id: Optional[int] = None
        name: str
        email: str
        age: Optional[int] = None

    # Define data access layer
    class UserResource(CRUDResource):
        async def list(self, filters, offset, limit, order_by):
            # Your DB query logic here
            return users, total_count

        async def get(self, id):
            return user

        async def create(self, data):
            return created_user

        async def update(self, id, data):
            return updated_user

        async def delete(self, id):
            return True

    # Generate REST API
    api = RestAPI(app, prefix="/api")
    api.register_resource("users", User, UserResource(),
                         policies={"GET": True, "POST": require_auth()})
"""

from typing import Any, Callable, Dict, List, Optional, Type, Union
from functools import wraps
import json
import asyncio
from datetime import datetime
from robyn import Response


class CRUDResource:
    """
    Base class for CRUD resources. Implement these methods to connect
    to your database/ORM of choice.
    """

    async def list(
        self,
        filters: Dict[str, Any],
        offset: int = 0,
        limit: int = 100,
        order_by: Optional[List[str]] = None
    ) -> tuple[List[Dict], int]:
        """
        List resources with filtering and pagination.

        Returns:
            (items, total_count)
        """
        raise NotImplementedError("list() must be implemented")

    async def get(self, id: Any) -> Optional[Dict]:
        """Get a single resource by ID"""
        raise NotImplementedError("get() must be implemented")

    async def create(self, data: Dict[str, Any]) -> Dict:
        """Create a new resource"""
        raise NotImplementedError("create() must be implemented")

    async def update(self, id: Any, data: Dict[str, Any]) -> Dict:
        """Update an existing resource"""
        raise NotImplementedError("update() must be implemented")

    async def delete(self, id: Any) -> bool:
        """Delete a resource"""
        raise NotImplementedError("delete() must be implemented")


class QueryParser:
    """Parse PyDAL-style query parameters"""

    OPERATORS = {
        'eq': lambda a, b: a == b,
        'ne': lambda a, b: a != b,
        'gt': lambda a, b: a > b,
        'ge': lambda a, b: a >= b,
        'lt': lambda a, b: a < b,
        'le': lambda a, b: a <= b,
        'in': lambda a, b: a in b,
        'like': lambda a, b: b in str(a),
    }

    @staticmethod
    def parse_filters(query_params: Dict[str, str]) -> Dict[str, Any]:
        """
        Parse query parameters into filters.

        Examples:
            ?name.eq=John -> {"name": {"eq": "John"}}
            ?age.gt=18 -> {"age": {"gt": 18}}
            ?status.in=active,pending -> {"status": {"in": ["active", "pending"]}}
        """
        filters = {}

        for key, value in query_params.items():
            if key.startswith('@'):
                continue  # Skip modifiers

            # Parse field.operator=value
            if '.' in key:
                field, operator = key.rsplit('.', 1)

                # Handle negation
                negate = False
                if operator.startswith('not.'):
                    negate = True
                    operator = operator[4:]

                if operator not in QueryParser.OPERATORS:
                    continue

                # Parse value
                if operator == 'in':
                    value = value.split(',')

                # Try to convert to int/float
                try:
                    if isinstance(value, list):
                        value = [QueryParser._try_convert(v) for v in value]
                    else:
                        value = QueryParser._try_convert(value)
                except:
                    pass

                if field not in filters:
                    filters[field] = {}

                filters[field][operator] = value
                if negate:
                    filters[field]['negate'] = True
            else:
                # Simple equality
                filters[key] = {'eq': QueryParser._try_convert(value)}

        return filters

    @staticmethod
    def _try_convert(value: str) -> Any:
        """Try to convert string to int, float, or bool"""
        if value.lower() == 'true':
            return True
        if value.lower() == 'false':
            return False
        if value.lower() == 'null':
            return None

        try:
            if '.' in value:
                return float(value)
            return int(value)
        except ValueError:
            return value

    @staticmethod
    def parse_modifiers(query_params: Dict[str, str]) -> Dict[str, Any]:
        """
        Parse query modifiers (@offset, @limit, @order, etc.)
        """
        modifiers = {
            'offset': 0,
            'limit': 100,
            'order_by': None,
        }

        if '@offset' in query_params:
            try:
                modifiers['offset'] = int(query_params['@offset'])
            except ValueError:
                pass

        if '@limit' in query_params:
            try:
                limit = int(query_params['@limit'])
                modifiers['limit'] = min(limit, 1000)  # Cap at 1000
            except ValueError:
                pass

        if '@order' in query_params:
            order = query_params['@order']
            if order.startswith('~'):
                modifiers['order_by'] = [f"-{order[1:]}"]
            else:
                modifiers['order_by'] = [order]

        return modifiers


class RestAPI:
    """
    REST API Generator for Robyn

    Auto-generates CRUD endpoints from Pydantic models.
    """

    def __init__(self, app, prefix: str = "/api", version: str = "1.0"):
        """
        Initialize REST API generator

        Args:
            app: Robyn app instance
            prefix: URL prefix for all API routes (default: "/api")
            version: API version string
        """
        self.app = app
        self.prefix = prefix.rstrip('/')
        self.version = version
        self.resources: Dict[str, Dict] = {}

    def register_resource(
        self,
        name: str,
        model: Type,
        resource: CRUDResource,
        policies: Optional[Dict[str, Union[bool, Callable]]] = None,
        rate_limits: Optional[Dict[str, tuple]] = None,
        tags: Optional[List[str]] = None,
    ):
        """
        Register a CRUD resource and auto-generate endpoints.

        Args:
            name: Resource name (e.g., "users", "posts")
            model: Pydantic model class
            resource: CRUDResource instance with data access methods
            policies: Per-method policies {"GET": True, "POST": require_auth()}
            rate_limits: Per-method rate limits {"GET": (100, 60), "POST": (10, 60)}
            tags: OpenAPI tags for documentation

        Example:
            api.register_resource(
                "users",
                User,
                UserResource(),
                policies={"GET": True, "POST": require_auth(), "DELETE": admin_required()},
                rate_limits={"POST": (10, 60)},
                tags=["Users"]
            )
        """
        # Default policies - only GET is allowed by default
        if policies is None:
            policies = {
                "GET": True,
                "POST": False,
                "PUT": False,
                "DELETE": False,
            }

        # Store resource metadata
        self.resources[name] = {
            "model": model,
            "resource": resource,
            "policies": policies,
            "rate_limits": rate_limits or {},
            "tags": tags or [name.capitalize()],
        }

        # Generate routes
        self._generate_list_route(name)
        self._generate_get_route(name)
        self._generate_create_route(name)
        self._generate_update_route(name)
        self._generate_delete_route(name)

    def _apply_policy(self, method: str, name: str, handler: Callable) -> Callable:
        """Apply policy decorator to a handler"""
        policy = self.resources[name]["policies"].get(method)

        if policy is False:
            # Method not allowed
            @wraps(handler)
            def forbidden(request):
                return Response(
                    status_code=405,
                    headers={"Content-Type": "application/json"},
                    body=self._response(
                        status="error",
                        code=405,
                        errors=[f"{method} not allowed for {name}"]
                    )
                )
            return forbidden
        elif policy is True:
            # No restrictions
            return handler
        elif callable(policy):
            # Apply decorator (e.g., require_auth())
            return policy(handler)
        else:
            return handler

    def _apply_rate_limit(self, method: str, name: str, handler: Callable) -> Callable:
        """Apply rate limiting decorator to a handler"""
        rate_limit_config = self.resources[name]["rate_limits"].get(method)

        if rate_limit_config:
            try:
                from robyn_extensions import rate_limit
                requests, per_seconds = rate_limit_config
                return rate_limit(requests=requests, per_seconds=per_seconds)(handler)
            except ImportError:
                pass

        return handler

    def _generate_list_route(self, name: str):
        """Generate GET /api/{name} endpoint"""
        resource_meta = self.resources[name]
        resource = resource_meta["resource"]

        def list_handler(request):
            # Parse query parameters
            query_params = {}
            if hasattr(request, 'query_params'):
                # Convert QueryParams object to dict
                qp = request.query_params
                if hasattr(qp, 'items'):
                    query_params = dict(qp.items())
                elif hasattr(qp, 'to_dict'):
                    query_params = qp.to_dict()
                else:
                    # Try to convert to dict directly
                    try:
                        query_params = dict(qp)
                    except:
                        query_params = {}
            elif hasattr(request, 'url'):
                # Parse from URL
                from urllib.parse import parse_qs, urlparse
                parsed = urlparse(request.url)
                query_params = {k: v[0] for k, v in parse_qs(parsed.query).items()}

            filters = QueryParser.parse_filters(query_params)
            modifiers = QueryParser.parse_modifiers(query_params)

            try:
                # Get or create event loop
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                items, total = loop.run_until_complete(resource.list(
                    filters,
                    offset=modifiers['offset'],
                    limit=modifiers['limit'],
                    order_by=modifiers['order_by']
                ))

                return self._response(
                    status="success",
                    code=200,
                    count=len(items),
                    items=items,
                    total=total,
                    offset=modifiers['offset'],
                    limit=modifiers['limit']
                )
            except Exception as e:
                return Response(
                    status_code=500,
                    headers={"Content-Type": "application/json"},
                    body=self._response(
                        status="error",
                        code=500,
                        errors=[str(e)]
                    )
                )

        # Apply decorators
        list_handler = self._apply_rate_limit("GET", name, list_handler)
        list_handler = self._apply_policy("GET", name, list_handler)

        # Register route
        route_path = f"{self.prefix}/{name}"
        self.app.get(route_path)(list_handler)

    def _generate_get_route(self, name: str):
        """Generate GET /api/{name}/{id} endpoint"""
        resource_meta = self.resources[name]
        resource = resource_meta["resource"]

        def get_handler(request):
            # Extract ID from path
            id_value = request.path_params.get("id")

            try:
                # Get or create event loop
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                item = loop.run_until_complete(resource.get(id_value))

                if item is None:
                    return Response(
                        status_code=404,
                        headers={"Content-Type": "application/json"},
                        body=self._response(
                            status="error",
                            code=404,
                            errors=[f"{name} with id={id_value} not found"]
                        )
                    )

                return self._response(
                    status="success",
                    code=200,
                    count=1,
                    items=[item]
                )
            except Exception as e:
                return Response(
                    status_code=500,
                    headers={"Content-Type": "application/json"},
                    body=self._response(
                        status="error",
                        code=500,
                        errors=[str(e)]
                    )
                )

        # Apply decorators
        get_handler = self._apply_rate_limit("GET", name, get_handler)
        get_handler = self._apply_policy("GET", name, get_handler)

        # Register route
        route_path = f"{self.prefix}/{name}/:id"
        self.app.get(route_path)(get_handler)

    def _generate_create_route(self, name: str):
        """Generate POST /api/{name} endpoint"""
        resource_meta = self.resources[name]
        resource = resource_meta["resource"]
        model = resource_meta["model"]

        def create_handler(request):
            try:
                # Parse request body
                if hasattr(request, 'json'):
                    data = request.json()
                else:
                    data = json.loads(request.body)

                # Validate with Pydantic model
                validated = model(**data)

                # Get or create event loop
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                # Create resource
                created = loop.run_until_complete(resource.create(validated.dict()))

                return Response(
                    status_code=201,
                    headers={"Content-Type": "application/json"},
                    body=self._response(
                        status="success",
                        code=201,
                        count=1,
                        items=[created]
                    )
                )
            except Exception as e:
                return Response(
                    status_code=400,
                    headers={"Content-Type": "application/json"},
                    body=self._response(
                        status="error",
                        code=400,
                        errors=[str(e)]
                    )
                )

        # Apply decorators
        create_handler = self._apply_rate_limit("POST", name, create_handler)
        create_handler = self._apply_policy("POST", name, create_handler)

        # Register route
        route_path = f"{self.prefix}/{name}"
        self.app.post(route_path)(create_handler)

    def _generate_update_route(self, name: str):
        """Generate PUT /api/{name}/{id} endpoint"""
        resource_meta = self.resources[name]
        resource = resource_meta["resource"]
        model = resource_meta["model"]

        def update_handler(request):
            id_value = request.path_params.get("id")

            try:
                # Parse request body
                if hasattr(request, 'json'):
                    data = request.json()
                else:
                    data = json.loads(request.body)

                # Validate with Pydantic model (allow partial updates)
                validated = model(**data)

                # Get or create event loop
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                # Update resource
                updated = loop.run_until_complete(resource.update(id_value, validated.dict(exclude_unset=True)))

                if updated is None:
                    return Response(
                        status_code=404,
                        headers={"Content-Type": "application/json"},
                        body=self._response(
                            status="error",
                            code=404,
                            errors=[f"{name} with id={id_value} not found"]
                        )
                    )

                return self._response(
                    status="success",
                    code=200,
                    count=1,
                    items=[updated]
                )
            except Exception as e:
                return Response(
                    status_code=400,
                    headers={"Content-Type": "application/json"},
                    body=self._response(
                        status="error",
                        code=400,
                        errors=[str(e)]
                    )
                )

        # Apply decorators
        update_handler = self._apply_rate_limit("PUT", name, update_handler)
        update_handler = self._apply_policy("PUT", name, update_handler)

        # Register route
        route_path = f"{self.prefix}/{name}/:id"
        self.app.put(route_path)(update_handler)

    def _generate_delete_route(self, name: str):
        """Generate DELETE /api/{name}/{id} endpoint"""
        resource_meta = self.resources[name]
        resource = resource_meta["resource"]

        def delete_handler(request):
            id_value = request.path_params.get("id")

            try:
                # Get or create event loop
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                success = loop.run_until_complete(resource.delete(id_value))

                if not success:
                    return Response(
                        status_code=404,
                        headers={"Content-Type": "application/json"},
                        body=self._response(
                            status="error",
                            code=404,
                            errors=[f"{name} with id={id_value} not found"]
                        )
                    )

                return self._response(
                    status="success",
                    code=200,
                    message=f"{name} deleted successfully"
                )
            except Exception as e:
                return Response(
                    status_code=500,
                    headers={"Content-Type": "application/json"},
                    body=self._response(
                        status="error",
                        code=500,
                        errors=[str(e)]
                    )
                )

        # Apply decorators
        delete_handler = self._apply_rate_limit("DELETE", name, delete_handler)
        delete_handler = self._apply_policy("DELETE", name, delete_handler)

        # Register route
        route_path = f"{self.prefix}/{name}/:id"
        self.app.delete(route_path)(delete_handler)

    def _response(
        self,
        status: str,
        code: int,
        count: int = 0,
        items: Optional[List] = None,
        total: Optional[int] = None,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
        message: Optional[str] = None,
        errors: Optional[List[str]] = None
    ) -> str:
        """
        Generate standardized API response (PyDAL-style)
        """
        response = {
            "api_version": self.version,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "status": status,
            "code": code,
        }

        if items is not None:
            response["count"] = count
            response["items"] = items

        if total is not None:
            response["total"] = total

        if offset is not None:
            response["offset"] = offset

        if limit is not None:
            response["limit"] = limit

        if message:
            response["message"] = message

        if errors:
            response["errors"] = errors

        return json.dumps(response)


__all__ = [
    "RestAPI",
    "CRUDResource",
    "QueryParser",
]
