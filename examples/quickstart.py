"""
Quick start example showing basic usage.
"""

from robyn import Robyn
from robyn_extensions import body, rate_limit
from pydantic import BaseModel

app = Robyn(__file__)


class User(BaseModel):
    name: str
    email: str
    age: int


@app.post("/users")
@body(User)
@rate_limit(requests=10, per_seconds=60)
def create_user(request, user: User):
    return {"message": f"Created user {user.name}"}


if __name__ == "__main__":
    app.start(port=8080)
