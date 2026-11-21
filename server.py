
import os
import logging

import uvicorn

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

from fastmcp import FastMCP
from fastmcp.server.auth import require_scopes
from fastmcp.server.auth.providers.descope import DescopeProvider
from fastmcp.server.auth.providers.jwt import JWTVerifier


# ==========================================
# 1. Configuration
# ==========================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp-playground")

DESCOPE_PROJECT_ID = "P3ML27ocPWZS6vulRanlFpjFkO20"

BASE_URL = (
    "https://mcp-playground-production.up.railway.app"
)

MCP_SERVER_URL = f"{BASE_URL}/mcp"

DESCOPE_ISSUER = (
    f"https://api.descope.com/v1/apps/"
    f"{DESCOPE_PROJECT_ID}"
)

DESCOPE_CONFIG_URL = (
    f"{DESCOPE_ISSUER}"
    "/.well-known/openid-configuration"
)

DESCOPE_JWKS_URL = (
    f"https://api.descope.com/"
    f"{DESCOPE_PROJECT_ID}"
    "/.well-known/jwks.json"
)

PORT = int(os.environ.get("PORT", "8080"))


# ==========================================
# 2. Descope JWT verification
# ==========================================

# Validate:
# - JWT signature using Descope JWKS
# - Descope issuer
# - Exact MCP resource audience
# - Token expiration

token_verifier = JWTVerifier(
    jwks_uri=DESCOPE_JWKS_URL,
    issuer=DESCOPE_ISSUER,
    audience=MCP_SERVER_URL,
    algorithm="RS256",
)


# ==========================================
# 3. Descope OAuth provider
# ==========================================

auth_provider = DescopeProvider(
    config_url=DESCOPE_CONFIG_URL,
    base_url=BASE_URL,
    scopes_supported=["hello:read"],
    required_scopes=["hello:read"],
    token_verifier=token_verifier,
)


# ==========================================
# 4. MCP Server
# ==========================================

mcp = FastMCP(
    name="My Descope Protected MCP Server",
    auth=auth_provider,
)


# ==========================================
# 5. Business Logic
# ==========================================

def hello(name: str) -> str:
    return (
        f"Hello {name}! "
        "This message is coming from my "
        "MCP server in the cloud."
    )


# ==========================================
# 6. Protected MCP Tool
# ==========================================

@mcp.tool(auth=require_scopes("hello:read"))
def say_hello(name: str) -> str:
    """
    Say hello to someone by name.

    Requires Descope OAuth authentication
    and the hello:read permission.
    """

    logger.info("Executing say_hello tool")

    return hello(name)


# ==========================================
# 7. FastAPI Web Application
# ==========================================

# Preserve MCP's startup/shutdown lifecycle.
mcp_app = mcp.http_app(path="/mcp")

app = FastAPI(
    title="MCP + Descope + Poppy Playground",
    version="2.0.0",
    lifespan=mcp_app.lifespan,
)


# ==========================================
# 8. Browser Homepage
# ==========================================

@app.get("/", response_class=HTMLResponse)
async def homepage():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>MCP Playground</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 750px;
                margin: 80px auto;
                padding: 20px;
                line-height: 1.8;
            }
            h1 { color: #333; }
            a { color: #0066cc; }
        </style>
    </head>
    <body>
        <h1>MCP + Descope + Poppy Playground</h1>

        <p>Application is running successfully.</p>

        <h3>Available Endpoints</h3>

        <ul>
            <li>
                <a href="/hello?name=Kishore">
                    Public Hello World REST API
                </a>
            </li>

            <li>
                <a href="/.well-known/poppy.json">
                    Poppy Discovery
                </a>
            </li>

            <li>
                <a href="/.well-known/oauth-protected-resource/mcp">
                    OAuth Protected Resource Metadata
                </a>
            </li>

            <li>
                <a href="/docs">
                    Swagger Documentation
                </a>
            </li>
        </ul>

        <p>
            MCP endpoint: <strong>/mcp</strong>
            (Descope authentication required)
        </p>
    </body>
    </html>
    """


# ==========================================
# 9. Public REST API
# ==========================================

@app.get("/hello")
async def rest_hello(name: str = "World"):
    return {
        "result": hello(name)
    }


# ==========================================
# 10. Health Check
# ==========================================

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "mcp-playground",
        "authentication": "descope"
    }


# ==========================================
# 11. Poppy Discovery
# ==========================================

@app.get("/.well-known/poppy.json")
async def poppy_discovery():
    return JSONResponse(
        content={
            "protocol_version": "1.0",
            "organization": {
                "name": "MCP Playground",
                "domain": (
                    "mcp-playground-production"
                    ".up.railway.app"
                )
            },
            "web": {}
        }
    )


# ==========================================
# 12. Mount MCP and OAuth Discovery
# ==========================================

# Mount at root so FastMCP can serve:
#
# /mcp
# /.well-known/oauth-protected-resource
# /.well-known/oauth-protected-resource/mcp
#
# FastAPI routes above take precedence.
# MCP authentication remains enforced
# by FastMCP's own middleware.

app.mount("/", mcp_app)


# ==========================================
# 13. Railway Startup
# ==========================================

if __name__ == "__main__":

    logger.info("Starting MCP Playground")
    logger.info("MCP URL: %s", MCP_SERVER_URL)
    logger.info("Descope issuer: %s", DESCOPE_ISSUER)
    logger.info("Required scope: hello:read")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=PORT,
        log_level="info"
    )
