"""Single-service MCP + REST + Poppy discovery playground.

This is deliberately a public, unauthenticated demo. Do not add real data or
sensitive operations before introducing authentication and authorization.
"""

import os
from html import escape

import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastmcp import FastMCP

DOMAIN = os.getenv("PUBLIC_DOMAIN", "mcp-playground-production.up.railway.app")


def hello(name: str) -> str:
    return f"Hello {name}! This message is coming from my MCP server in the cloud."


mcp = FastMCP("My First MCP Server")


@mcp.tool
def say_hello(name: str) -> str:
    """Say hello to someone by name."""
    return hello(name)


# Host FastMCP at /mcp without changing the existing remote MCP URL.
# Mount the MCP app at / only AFTER the ordinary FastAPI routes below.
mcp_app = mcp.http_app(path="/mcp")
app = FastAPI(
    title="MCP and Poppy Playground",
    version="1.0.0",
    lifespan=mcp_app.lifespan,
)


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def homepage():
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>MCP &amp; Poppy Playground</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 720px; margin: 5rem auto;
           padding: 0 1.25rem; line-height: 1.6; }
    a { color: #155eef; } li { margin: .65rem 0; }
    code { background: #f2f4f7; padding: .15rem .3rem; border-radius: .25rem; }
  </style>
</head>
<body>
  <h1>MCP &amp; Poppy Playground</h1>
  <p>Application is running successfully.</p>
  <ul>
    <li><a href="/hello?name=Kishore">Hello World REST API</a></li>
    <li><a href="/.well-known/poppy.json">Poppy discovery document</a></li>
    <li><a href="/docs">OpenAPI / Swagger documentation</a></li>
    <li><a href="/health">Health check</a></li>
  </ul>
  <p>MCP clients connect to <code>/mcp</code>; this is not a browser page.</p>
  <p><small>POC only: no authentication configured.</small></p>
</body>
</html>"""


@app.get("/hello")
def rest_hello(name: str = "World"):
    return {"result": hello(name)}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/.well-known/poppy.json", include_in_schema=False)
def poppy_discovery():
    """Discovery-only Poppy metadata (no OAuth/Descope configured)."""
    return JSONResponse({
        "protocol_version": "1.0",
        "organization": {
            "name": "MCP Playground",
            "domain": DOMAIN,
        },
        "web": {},
    })


# IMPORTANT: this catch-all mount belongs after the FastAPI routes.
app.mount("/", mcp_app)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
