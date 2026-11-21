
import os

import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastmcp import FastMCP

# ------------------------------------
# Configuration
# ------------------------------------

HOST = "mcp-playground-production.up.railway.app"
BASE_URL = f"https://{HOST}"

# ------------------------------------
# Business logic
# ------------------------------------

def hello(name: str) -> str:
    return (
        f"Hello {name}! This message is coming "
        f"from my MCP server in the cloud."
    )

# ------------------------------------
# MCP server
# ------------------------------------

mcp = FastMCP("My First MCP Server")


@mcp.tool
def say_hello(name: str) -> str:
    """Say hello to someone by name."""
    return hello(name)


# ------------------------------------
# FastAPI application
# ------------------------------------

mcp_app = mcp.http_app(path="/mcp")
app = FastAPI(
    title="MCP and Poppy Playground",
    version="1.0.0",
    lifespan=mcp_app.lifespan,
)


# ------------------------------------
# Browser homepage
# ------------------------------------

@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>MCP & Poppy Playground</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 700px;
                margin: 80px auto;
                padding: 20px;
                line-height: 1.8;
            }
            h1 { color: #333; }
            a { color: #0066cc; }
        </style>
    </head>
    <body>
        <h1>My MCP & Poppy Playground</h1>
        <p>Application is running successfully!</p>

        <h3>Available endpoints</h3>
        <ul>
            <li><a href="/hello?name=Kishore">
                Hello World REST API</a></li>
            <li><a href="/.well-known/poppy.json">
                Poppy Discovery</a></li>
            <li><a href="/docs">
                REST API Documentation</a></li>
            <li><a href="/mcp">
                MCP Endpoint</a></li>
        </ul>
    </body>
    </html>
    """


# ------------------------------------
# REST API
# ------------------------------------

@app.get("/hello")
def rest_hello(name: str = "World"):
    return {
        "result": hello(name)
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


# ------------------------------------
# Poppy discovery document
# ------------------------------------

@app.get("/.well-known/poppy.json")
def poppy_discovery():
    return JSONResponse(
        content={
            "protocol_version": "1.0",
            "organization": {
                "name": "MCP Playground",
                "domain": HOST
            },
            "web": {}
        }
    )


# ------------------------------------
# Mount existing MCP endpoint
# ------------------------------------

app.mount("/", mcp_app)


# ------------------------------------
# Railway startup
# ------------------------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port
    )
