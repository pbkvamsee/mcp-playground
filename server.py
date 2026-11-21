"""Railway POC: browser REST API + existing FastMCP + Poppy discovery + Descope OAuth.

Protected REST calls validate JWT signature, issuer, audience, scopes, and
(optional but enabled by default) live token introspection. This is NOT a
full Poppy agent-session verifier; Poppy-Session claims are never trusted.
"""
import os
from functools import lru_cache
from html import escape

import httpx
import jwt
import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Security, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import OAuth2AuthorizationCodeBearer, SecurityScopes
from fastmcp import FastMCP
from jwt import PyJWKClient
from jwt.exceptions import PyJWTError

DOMAIN = os.getenv("PUBLIC_DOMAIN", "mcp-playground-production.up.railway.app").strip().removeprefix("https://").strip("/")
ORIGIN = f"https://{DOMAIN}"
DESCOPE_PROJECT_ID = os.getenv("DESCOPE_PROJECT_ID", "P3ML27ocPWZS6vulRanlFpjFkO20")
DESCOPE_BASE_URL = os.getenv("DESCOPE_BASE_URL", "https://api.descope.com").rstrip("/")
DESCOPE_ISSUER = os.getenv("DESCOPE_ISSUER", f"{DESCOPE_BASE_URL}/v1/apps/{DESCOPE_PROJECT_ID}")
# Read this exact HTTPS URL from your Descope discovery document's 'jwks_uri'.
DESCOPE_JWKS_URL = os.getenv("DESCOPE_JWKS_URL", "").strip()
DESCOPE_CLIENT_ID = os.getenv("DESCOPE_CLIENT_ID", "").strip()
DESCOPE_CLIENT_SECRET = os.getenv("DESCOPE_CLIENT_SECRET", "").strip()
# API audience must exactly match the Resource identifier registered in Descope.
RESOURCE_ID = ORIGIN
HELLO_SCOPE = "hello:read"
INTROSPECT_URL = f"{DESCOPE_BASE_URL}/oauth2/v1/apps/introspect"


def hello(name: str) -> str:
    return f"Hello {name}! This message is coming from my MCP server in the cloud."


mcp = FastMCP("My First MCP Server")


@mcp.tool
async def say_hello(name: str) -> str:
    """Say hello to someone by name (public demo MCP tool)."""
    return hello(name)


mcp_app = mcp.http_app(path="/mcp")
app = FastAPI(title="MCP & Poppy Playground", version="2.0.0", lifespan=mcp_app.lifespan)

oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl=f"{DESCOPE_BASE_URL}/oauth2/v1/apps/authorize",
    tokenUrl=f"{DESCOPE_BASE_URL}/oauth2/v1/apps/token",
    scopes={HELLO_SCOPE: "Call the protected Hello World REST API"},
)


@lru_cache(maxsize=1)
def jwks_client() -> PyJWKClient:
    if not DESCOPE_JWKS_URL.startswith("https://"):
        raise HTTPException(503, "DESCOPE_JWKS_URL must be configured with the issuer's HTTPS jwks_uri")
    return PyJWKClient(DESCOPE_JWKS_URL, cache_jwk_set=True, lifespan=300, timeout=5)


async def require_descope_token(
    security_scopes: SecurityScopes,
    token: str = Depends(oauth2_scheme),
) -> dict:
    """Fail-closed resource-server authentication and authorization.

    This only authorizes the *OAuth user/account*. It does not authenticate
    Poppy-Session agent identity or validate DPoP sender constraints.
    """
    challenge = f'Bearer realm="{RESOURCE_ID}"'
    try:
        signing_key = jwks_client().get_signing_key_from_jwt(token).key
        claims = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256", "ES256"],
            issuer=DESCOPE_ISSUER,
            audience=RESOURCE_ID,
            options={"require": ["exp", "iss", "aud", "sub"]},
            leeway=30,
        )
    except HTTPException:
        raise
    except (PyJWTError, ValueError, OSError) as exc:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": challenge},
        ) from exc

    raw_scopes = claims.get("scope", "")
    token_scopes = set(raw_scopes.split()) if isinstance(raw_scopes, str) else set(raw_scopes) if isinstance(raw_scopes, list) else set()
    for required_scope in security_scopes.scopes:
        if required_scope not in token_scopes:
            raise HTTPException(
                status_code=403,
                detail=f"Missing required scope: {required_scope}",
                headers={"WWW-Authenticate": f'{challenge}, error="insufficient_scope", scope="{required_scope}"'},
            )

    # RFC 7662: check live status so a revoked token is not honored until expiry.
    # Configure a confidential OAuth client authorized to introspect these tokens.
    if not DESCOPE_CLIENT_ID or not DESCOPE_CLIENT_SECRET:
        raise HTTPException(503, "Descope introspection client credentials are not configured")
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.post(
                INTROSPECT_URL,
                data={"token": token, "token_type_hint": "access_token"},
                auth=(DESCOPE_CLIENT_ID, DESCOPE_CLIENT_SECRET),
            )
            response.raise_for_status()
            info = response.json()
        if info.get("active") is not True:
            raise HTTPException(401, "Token is inactive", headers={"WWW-Authenticate": challenge})
        # Where Descope returns these fields, require them to agree with the JWT.
        if "aud" in info:
            audiences = info["aud"] if isinstance(info["aud"], list) else [info["aud"]]
            if RESOURCE_ID not in audiences:
                raise HTTPException(401, "Introspection audience mismatch", headers={"WWW-Authenticate": challenge})
        if "sub" in info and info["sub"] != claims["sub"]:
            raise HTTPException(401, "Introspection subject mismatch", headers={"WWW-Authenticate": challenge})
    except HTTPException:
        raise
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(503, "Unable to validate token status with Descope") from exc
    return claims


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def homepage():
    safe_domain = escape(DOMAIN)
    return f"""<!doctype html><html lang='en'><head><meta charset='utf-8'>
<meta name='viewport' content='width=device-width, initial-scale=1'>
<title>MCP &amp; Poppy Playground</title>
<style>body{{font:16px system-ui,sans-serif;max-width:750px;margin:5rem auto;padding:1.3rem;line-height:1.7}}
a{{color:#1357a6}}code{{background:#f2f4f7;padding:3px 6px}}li{{margin:10px 0}}</style>
</head><body><h1>MCP &amp; Poppy Playground</h1>
<p>Running on <strong>{safe_domain}</strong></p><ul>
<li><a href='/hello?name=Kishore'>Public Hello World REST API</a></li>
<li><a href='/docs'>OpenAPI documentation (protected endpoint included)</a></li>
<li><a href='/.well-known/poppy.json'>Poppy discovery</a></li>
<li><a href='/.well-known/oauth-protected-resource'>OAuth protected-resource metadata</a></li>
<li><a href='/health'>Health check</a></li>
</ul><p>MCP endpoint: <code>/mcp</code> (use an MCP client, not the browser).</p>
<p>Protected endpoint: <code>/api/hello?name=Kishore</code> — requires a valid Descope access token with <code>hello:read</code>.</p>
<p><small>POC: MCP and public /hello are unauthenticated. Do not put customer data here.</small></p>
</body></html>"""


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/hello")
def public_hello(name: str = "World"):
    return {"result": hello(name)}


@app.get("/api/hello")
async def protected_hello(name: str = "World", claims: dict = Security(require_descope_token, scopes=[HELLO_SCOPE])):
    # Deliberately does not read Poppy-Session or treat unverified client data as identity.
    return {"result": hello(name), "authenticated_subject": claims["sub"]}


@app.get("/.well-known/poppy.json", include_in_schema=False)
def poppy_discovery():
    return JSONResponse({
        "protocol_version": "1.0",
        "organization": {"name": "MCP Playground", "domain": DOMAIN},
        "auth": {
            "issuer": DESCOPE_ISSUER,
            "scopes": {HELLO_SCOPE: "Read a personalized Hello World response"},
            "scope_hints": {HELLO_SCOPE: {"changes": "none", "personal_data": False}},
        },
        "apis": [{
            "type": "openapi",
            "url": f"{ORIGIN}/openapi.json",
            "description": "Public and OAuth-protected Hello World APIs",
        }],
        "web": {},
    })


@app.get("/.well-known/oauth-protected-resource", include_in_schema=False)
def oauth_protected_resource():
    return JSONResponse({
        "resource": RESOURCE_ID,
        "authorization_servers": [DESCOPE_ISSUER],
        "scopes_supported": [HELLO_SCOPE],
    })


# Keep existing /mcp URL. Mount last so FastAPI routes resolve first.
app.mount("/", mcp_app)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
