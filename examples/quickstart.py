"""
Quick start example — minimal Robyn app with validation and rate limiting.
"""

from robyn import Robyn, Request
from robyn_extensions import BaseModel, Field, body_v2, rate_limit

app = Robyn(__file__)


class User(BaseModel):
    name: str = Field(min_length=2, max_length=50)
    email: str
    age: int = Field(ge=0, le=150)


@app.post("/users")
@body_v2(User)
@rate_limit(requests=10, per_seconds=60)
def create_user(request: Request, user: User):
    return {"message": f"Created user {user.name}", "data": user.model_dump()}


@app.get("/health")
def health(request: Request):
    return {"status": "ok"}


if __name__ == "__main__":
    app.start(port=8080)
