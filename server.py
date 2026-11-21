
import os
import logging

import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

from fastmcp import FastMCP
from fastmcp.server.auth import (
    RemoteAuthProvider,
    require_scopes,
)
from fastmcp.server.auth.providers.jwt import JWTVerifier
from pydantic import AnyHttpUrl


# ==========================================
# 1. Configuration
# ==========================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp-playground")

DESCOPE_PROJECT_ID = (
    "P3ML27ocPWZS6vulRanlFpjFkO20"
)

BASE_URL = (
    "https://mcp-playground-production.up.railway.app"
)

MCP_SERVER_URL = f"{BASE_URL}/mcp"

DESCOPE_ISSUER = (
    f"https://api.descope.com/v1/apps/"
    f"{DESCOPE_PROJECT_ID}"
)

DESCOPE_JWKS_URL = (
    f"https://api.descope.com/"
    f"{DESCOPE_PROJECT_ID}"
    "/.well-known/jwks.json"
)

REQUIRED_SCOPE = "hello:read"

PORT = int(os.environ.get("PORT", "8080"))


# ==========================================
# 2. Validate Descope Access Tokens
# ==========================================

token_verifier = JWTVerifier(
    jwks_uri=DESCOPE_JWKS_URL,
    issuer=DESCOPE_ISSUER,
    audience=MCP_SERVER_URL,
    required_scopes=[REQUIRED_SCOPE],
)


# ==========================================
# 3. OAuth Resource Server
# ==========================================

auth_provider = RemoteAuthProvider(
    token_verifier=token_verifier,
    authorization_servers=[
        AnyHttpUrl(DESCOPE_ISSUER)
    ],
    base_url=BASE_URL,
    scopes_supported=[REQUIRED_SCOPE],
)


# ==========================================
# 4. Create Protected MCP Server
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
    Say hello to a person.

    Requires Descope OAuth authentication
    and the hello:read permission.
    """

    logger.info("Executing say_hello")

    return hello(name)


# ==========================================
# 7. FastAPI + MCP Application
# ==========================================

mcp_app = mcp.http_app(path="/mcp")

app = FastAPI(
    title="MCP + Descope + Poppy Playground",
    version="3.0.0",
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
                margin: 70px auto;
                padding: 20px;
                line-height: 1.8;
            }
            h1 { color: #333; }
            a { color: #0066cc; }
            .status {
                color: green;
                font-weight: bold;
            }
        </style>
    </head>
    <body>
        <h1>MCP + Descope + Poppy</h1>

        <p class="status">
            Application is running!
        </p>

        <h3>Available Endpoints</h3>

        <ul>
            <li>
                <a href="/hello?name=Kishore">
                    Public Hello World REST API
                </a>
            </li>

            <li>
                <a href="/health">
                    Health Check
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
                    Swagger API Documentation
                </a>
            </li>
        </ul>

        <h3>MCP Endpoint</h3>

        <p><code>/mcp</code></p>

        <p>
            Descope OAuth authentication and
            hello:read permission are required.
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
        "mcp_authentication": "required",
        "oauth_provider": "Descope",
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
                ),
            },
            "web": {},
        }
    )


# ==========================================
# 12. Mount MCP Server
# ==========================================

# FastMCP serves:
# /mcp
# /.well-known/oauth-protected-resource
# /.well-known/oauth-protected-resource/mcp
#
# Authentication is enforced by FastMCP.

app.mount("/", mcp_app)


# ==========================================
# 13. Railway Startup
# ==========================================

if __name__ == "__main__":

    logger.info("Starting MCP Playground")
    logger.info("MCP URL: %s", MCP_SERVER_URL)
    logger.info("Descope issuer: %s", DESCOPE_ISSUER)
    logger.info("Audience: %s", MCP_SERVER_URL)
    logger.info("Required scope: %s", REQUIRED_SCOPE)

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=PORT,
        log_level="info",
    )
