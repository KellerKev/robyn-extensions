"""
OAuth authentication example with JWKS.
"""

from robyn import Robyn
from robyn_extensions import oauth, body
from pydantic import BaseModel

app = Robyn(__file__)

# Configure OAuth with Auth0 / Azure AD / other provider
# app.config.oauth.jwks_url = "https://your-auth-provider.com/.well-known/jwks.json"
# app.config.oauth.audience = "your-api-audience"
# app.config.oauth.issuer = "https://your-auth-provider.com/"


class Message(BaseModel):
    content: str


@app.get("/public")
def public_endpoint(request):
    return {"message": "This is public"}


@app.get("/protected")
@oauth(
    jwks_url="https://your-auth.com/.well-known/jwks.json",
    audience="your-api",
    issuer="https://your-auth.com/"
)
def protected_endpoint(request):
    user = request.user
    return {
        "message": "You are authenticated!",
        "user_id": user.sub,
        "claims": user.extra
    }


@app.post("/messages")
@oauth(required=True)
@body(Message)
def create_message(request, message: Message):
    user = request.user
    return {
        "message": message.content,
        "created_by": user.sub
    }


if __name__ == "__main__":
    app.start(port=8080)
