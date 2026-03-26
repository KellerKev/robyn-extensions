"""
REST API generator example — auto-generate CRUD endpoints with filtering and pagination.

Demonstrates:
  - CRUDResource implementation
  - Auto-generated CRUD routes
  - Per-method access policies
  - Per-method rate limits
  - PyDAL-style query filtering and pagination
"""

from robyn import Robyn, Request
from robyn_extensions import (
    RestAPI, CRUDResource, QueryParser,
    BaseModel, Field,
    require_auth, admin_required,
)
from typing import Optional, List, Dict, Any, Tuple

app = Robyn(__file__)


# === Models ===

class Product(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    price: float = Field(gt=0)
    category: str
    in_stock: bool = Field(default=True)
    description: Optional[str] = None


# === In-memory data store (replace with your database) ===

class ProductResource(CRUDResource):
    def __init__(self):
        self.db: Dict[str, Dict] = {}
        self.next_id = 1

    async def list(self, filters, offset=0, limit=100, order_by=None) -> Tuple[List[Dict], int]:
        items = list(self.db.values())

        # Apply filters (simplified — real implementation would use QueryParser operators)
        for field, conditions in filters.items():
            for op, value in conditions.items():
                if op == "eq":
                    items = [i for i in items if i.get(field) == value]
                elif op == "gt":
                    items = [i for i in items if i.get(field, 0) > float(value)]
                elif op == "lt":
                    items = [i for i in items if i.get(field, 0) < float(value)]
                elif op == "like":
                    items = [i for i in items if value.lower() in str(i.get(field, "")).lower()]

        total = len(items)

        # Apply ordering
        if order_by:
            desc = order_by.startswith("~")
            key = order_by.lstrip("~")
            items.sort(key=lambda x: x.get(key, ""), reverse=desc)

        # Apply pagination
        items = items[offset:offset + limit]

        return items, total

    async def get(self, id) -> Optional[Dict]:
        return self.db.get(str(id))

    async def create(self, data: Dict) -> Dict:
        item = {**data, "id": self.next_id}
        self.db[str(self.next_id)] = item
        self.next_id += 1
        return item

    async def update(self, id, data: Dict) -> Optional[Dict]:
        key = str(id)
        if key in self.db:
            self.db[key].update(data)
            return self.db[key]
        return None

    async def delete(self, id) -> bool:
        return self.db.pop(str(id), None) is not None


# === Register the REST API ===

api = RestAPI(app, prefix="/api/v1")

api.register_resource(
    "products",
    Product,
    ProductResource(),
    policies={
        "GET": True,                  # Public read access
        "POST": True,                 # Auth: require_auth()
        "PUT": True,                  # Auth: require_auth()
        "DELETE": True,               # Admin: admin_required()
    },
    rate_limits={
        "GET": (100, 60),            # 100 reads per minute
        "POST": (10, 60),            # 10 creates per minute
        "PUT": (20, 60),             # 20 updates per minute
        "DELETE": (5, 60),           # 5 deletes per minute
    },
    tags=["Products"]
)

# With auth enabled, you would use:
# policies={
#     "GET": True,
#     "POST": require_auth(),
#     "PUT": require_auth(),
#     "DELETE": admin_required(),
# }


# === Query Examples ===
#
# List all products:
#   GET /api/v1/products
#
# Filter by category:
#   GET /api/v1/products?category.eq=electronics
#
# Price range:
#   GET /api/v1/products?price.gt=10&price.lt=100
#
# Search by name:
#   GET /api/v1/products?name.like=widget
#
# Pagination:
#   GET /api/v1/products?@limit=20&@offset=40
#
# Sort by price (ascending):
#   GET /api/v1/products?@order=price
#
# Sort by price (descending):
#   GET /api/v1/products?@order=~price
#
# Combined:
#   GET /api/v1/products?category.eq=electronics&price.gt=10&@limit=20&@order=~price


if __name__ == "__main__":
    app.start(port=8080)
