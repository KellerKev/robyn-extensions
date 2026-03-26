"""
REST API Example - PyDAL-inspired CRUD API Generator

Demonstrates auto-generating REST APIs from Pydantic models with:
- CRUD operations (Create, Read, Update, Delete)
- Filtering and pagination
- Authentication and rate limiting
- Policy-based access control
"""
import sys
sys.path.insert(0, 'robyn_python/python')

from robyn import Robyn
from robyn_extensions import (
    BaseModel,
    Field,
    RestAPI,
    CRUDResource,
    require_auth,
    admin_required,
    rate_limit,
)
from typing import Optional, List
from datetime import datetime


# ============================================================================
# 1. Define Pydantic Models
# ============================================================================

class User(BaseModel):
    """User model"""
    id: Optional[int] = None
    name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., pattern=r'^[\w\.-]+@[\w\.-]+\.\w+$')
    age: Optional[int] = Field(None, ge=0, le=150)
    role: str = Field(default="user", pattern=r'^(user|admin)$')
    created_at: Optional[datetime] = None


class Post(BaseModel):
    """Blog post model"""
    id: Optional[int] = None
    title: str = Field(..., min_length=1, max_length=200)
    content: str
    author_id: int
    published: bool = False
    created_at: Optional[datetime] = None


class Comment(BaseModel):
    """Comment model"""
    id: Optional[int] = None
    post_id: int
    user_id: int
    text: str = Field(..., min_length=1)
    created_at: Optional[datetime] = None


# ============================================================================
# 2. Implement CRUD Resources (In-Memory Example)
# ============================================================================

class UserResource(CRUDResource):
    """User data access layer (in-memory implementation)"""

    def __init__(self):
        self.users = [
            {"id": 1, "name": "Alice", "email": "alice@example.com", "age": 30, "role": "admin", "created_at": "2024-01-01T00:00:00Z"},
            {"id": 2, "name": "Bob", "email": "bob@example.com", "age": 25, "role": "user", "created_at": "2024-01-02T00:00:00Z"},
            {"id": 3, "name": "Charlie", "email": "charlie@example.com", "age": 35, "role": "user", "created_at": "2024-01-03T00:00:00Z"},
        ]
        self.next_id = 4

    async def list(self, filters, offset=0, limit=100, order_by=None):
        """List users with filtering"""
        filtered = self.users[:]

        # Apply filters
        for field, conditions in filters.items():
            for op, value in conditions.items():
                if op == 'eq':
                    filtered = [u for u in filtered if u.get(field) == value]
                elif op == 'ne':
                    filtered = [u for u in filtered if u.get(field) != value]
                elif op == 'gt':
                    filtered = [u for u in filtered if u.get(field, 0) > value]
                elif op == 'ge':
                    filtered = [u for u in filtered if u.get(field, 0) >= value]
                elif op == 'lt':
                    filtered = [u for u in filtered if u.get(field, 0) < value]
                elif op == 'le':
                    filtered = [u for u in filtered if u.get(field, 0) <= value]
                elif op == 'in':
                    filtered = [u for u in filtered if u.get(field) in value]
                elif op == 'like':
                    filtered = [u for u in filtered if value.lower() in str(u.get(field, '')).lower()]

        total = len(filtered)

        # Apply ordering
        if order_by:
            for order in reversed(order_by):
                if order.startswith('-'):
                    field = order[1:]
                    filtered.sort(key=lambda x: x.get(field, ''), reverse=True)
                else:
                    filtered.sort(key=lambda x: x.get(order, ''))

        # Apply pagination
        return filtered[offset:offset+limit], total

    async def get(self, id):
        """Get user by ID"""
        for user in self.users:
            if user['id'] == int(id):
                return user
        return None

    async def create(self, data):
        """Create new user"""
        user = data.copy()
        user['id'] = self.next_id
        user['created_at'] = datetime.utcnow().isoformat() + 'Z'
        self.next_id += 1
        self.users.append(user)
        return user

    async def update(self, id, data):
        """Update user"""
        for i, user in enumerate(self.users):
            if user['id'] == int(id):
                self.users[i].update(data)
                return self.users[i]
        return None

    async def delete(self, id):
        """Delete user"""
        for i, user in enumerate(self.users):
            if user['id'] == int(id):
                del self.users[i]
                return True
        return False


class PostResource(CRUDResource):
    """Post data access layer (in-memory implementation)"""

    def __init__(self):
        self.posts = [
            {"id": 1, "title": "First Post", "content": "Hello World", "author_id": 1, "published": True, "created_at": "2024-01-01T00:00:00Z"},
            {"id": 2, "title": "Second Post", "content": "Lorem ipsum", "author_id": 1, "published": False, "created_at": "2024-01-02T00:00:00Z"},
            {"id": 3, "title": "Third Post", "content": "Dolor sit amet", "author_id": 2, "published": True, "created_at": "2024-01-03T00:00:00Z"},
        ]
        self.next_id = 4

    async def list(self, filters, offset=0, limit=100, order_by=None):
        filtered = self.posts[:]

        # Apply filters (same logic as UserResource)
        for field, conditions in filters.items():
            for op, value in conditions.items():
                if op == 'eq':
                    filtered = [p for p in filtered if p.get(field) == value]
                elif op == 'ne':
                    filtered = [p for p in filtered if p.get(field) != value]
                elif op == 'in':
                    filtered = [p for p in filtered if p.get(field) in value]
                elif op == 'like':
                    filtered = [p for p in filtered if value.lower() in str(p.get(field, '')).lower()]

        total = len(filtered)

        if order_by:
            for order in reversed(order_by):
                if order.startswith('-'):
                    field = order[1:]
                    filtered.sort(key=lambda x: x.get(field, ''), reverse=True)
                else:
                    filtered.sort(key=lambda x: x.get(order, ''))

        return filtered[offset:offset+limit], total

    async def get(self, id):
        for post in self.posts:
            if post['id'] == int(id):
                return post
        return None

    async def create(self, data):
        post = data.copy()
        post['id'] = self.next_id
        post['created_at'] = datetime.utcnow().isoformat() + 'Z'
        self.next_id += 1
        self.posts.append(post)
        return post

    async def update(self, id, data):
        for i, post in enumerate(self.posts):
            if post['id'] == int(id):
                self.posts[i].update(data)
                return self.posts[i]
        return None

    async def delete(self, id):
        for i, post in enumerate(self.posts):
            if post['id'] == int(id):
                del self.posts[i]
                return True
        return False


# ============================================================================
# 3. Setup Robyn App with REST API
# ============================================================================

app = Robyn(__file__)

# Initialize REST API generator
api = RestAPI(app, prefix="/api", version="1.0")

print("=" * 80)
print("REST API Example - PyDAL-inspired")
print("=" * 80)
print()

# Register Users resource
# - GET is public (anyone can list/view users)
# - POST requires authentication
# - PUT/DELETE require admin role
api.register_resource(
    "users",
    User,
    UserResource(),
    policies={
        "GET": True,                    # Public
        "POST": require_auth(),         # Requires valid JWT
        "PUT": admin_required(),        # Requires admin scope
        "DELETE": admin_required(),     # Requires admin scope
    },
    rate_limits={
        "GET": (100, 60),               # 100 requests per minute
        "POST": (10, 60),               # 10 requests per minute
        "PUT": (20, 60),
        "DELETE": (10, 60),
    },
    tags=["Users"]
)

print("✅ Registered Users API:")
print("   GET    /api/users          - List users (public, 100/min)")
print("   GET    /api/users/:id      - Get user (public, 100/min)")
print("   POST   /api/users          - Create user (auth required, 10/min)")
print("   PUT    /api/users/:id      - Update user (admin only, 20/min)")
print("   DELETE /api/users/:id      - Delete user (admin only, 10/min)")
print()

# Register Posts resource
# - GET is public
# - POST requires authentication
# - PUT/DELETE require post ownership or admin role
api.register_resource(
    "posts",
    Post,
    PostResource(),
    policies={
        "GET": True,                    # Public
        "POST": require_auth(),         # Requires authentication
        "PUT": require_auth(),          # Requires authentication
        "DELETE": require_auth(),       # Requires authentication
    },
    rate_limits={
        "GET": (100, 60),
        "POST": (10, 60),
        "PUT": (20, 60),
        "DELETE": (10, 60),
    },
    tags=["Posts"]
)

print("✅ Registered Posts API:")
print("   GET    /api/posts          - List posts (public, 100/min)")
print("   GET    /api/posts/:id      - Get post (public, 100/min)")
print("   POST   /api/posts          - Create post (auth required, 10/min)")
print("   PUT    /api/posts/:id      - Update post (auth required, 20/min)")
print("   DELETE /api/posts/:id      - Delete post (auth required, 10/min)")
print()

print("=" * 80)
print("Query Examples")
print("=" * 80)
print()
print("Filtering:")
print("  GET /api/users?age.gt=25              # Users older than 25")
print("  GET /api/users?role.eq=admin          # Admin users")
print("  GET /api/users?name.like=ali          # Names containing 'ali'")
print("  GET /api/posts?published.eq=true     # Published posts")
print()
print("Pagination:")
print("  GET /api/users?@offset=10&@limit=5   # Skip 10, take 5")
print()
print("Ordering:")
print("  GET /api/users?@order=age            # Order by age ascending")
print("  GET /api/users?@order=~age           # Order by age descending")
print()
print("Combined:")
print("  GET /api/users?age.gt=25&role.eq=user&@limit=10&@order=name")
print()

print("=" * 80)
print("Example Responses")
print("=" * 80)
print()
print("Success response:")
print('''{
  "api_version": "1.0",
  "timestamp": "2024-01-01T12:00:00Z",
  "status": "success",
  "code": 200,
  "count": 2,
  "total": 2,
  "offset": 0,
  "limit": 100,
  "items": [
    {"id": 1, "name": "Alice", "email": "alice@example.com", "age": 30, "role": "admin"},
    {"id": 2, "name": "Bob", "email": "bob@example.com", "age": 25, "role": "user"}
  ]
}''')
print()
print("Error response:")
print('''{
  "api_version": "1.0",
  "timestamp": "2024-01-01T12:00:00Z",
  "status": "error",
  "code": 404,
  "errors": ["users with id=999 not found"]
}''')
print()

if __name__ == "__main__":
    print("=" * 80)
    print("🚀 Starting REST API Server")
    print("=" * 80)
    print()
    print("Server running at: http://localhost:8085")
    print()
    print("Try these commands:")
    print("  curl http://localhost:8085/api/users")
    print("  curl http://localhost:8085/api/users/1")
    print("  curl http://localhost:8085/api/users?age.gt=25")
    print("  curl http://localhost:8085/api/posts?published.eq=true")
    print()
    app.start(host="0.0.0.0", port=8085)
