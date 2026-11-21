"""Descope-protected FastMCP airline playground. All airline data is synthetic.

The existing hello:read permission is reused for ALL tools during this learning
phase. Demo checkout links do not reserve seats, charge money or write bookings.
"""

import logging
import os
from datetime import date
from html import escape
from urllib.parse import urlencode

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastmcp import FastMCP
from fastmcp.server.auth import RemoteAuthProvider, require_scopes
from fastmcp.server.auth.providers.jwt import JWTVerifier
from pydantic import AnyHttpUrl

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp-playground")

DESCOPE_PROJECT_ID = os.environ.get("DESCOPE_PROJECT_ID", "P3ML27ocPWZS6vulRanlFpjFkO20")
BASE_URL = os.environ.get("BASE_URL", "https://mcp-playground-production.up.railway.app").rstrip("/")
MCP_SERVER_URL = f"{BASE_URL}/mcp"
DESCOPE_ISSUER = f"https://api.descope.com/v1/apps/{DESCOPE_PROJECT_ID}"
DESCOPE_JWKS_URL = f"https://api.descope.com/{DESCOPE_PROJECT_ID}/.well-known/jwks.json"
REQUIRED_SCOPE = "hello:read"  # Temporary shared scope; split by tool in phase 2.
PORT = int(os.environ.get("PORT", "8080"))

AIRPORTS = {
    "ORD": {"name": "O'Hare International Airport", "city": "Chicago", "country": "United States"},
    "IST": {"name": "Istanbul Airport", "city": "Istanbul", "country": "Türkiye"},
    "MKE": {"name": "Milwaukee Mitchell International Airport", "city": "Milwaukee", "country": "United States"},
    "JFK": {"name": "John F. Kennedy International Airport", "city": "New York", "country": "United States"},
    "LHR": {"name": "Heathrow Airport", "city": "London", "country": "United Kingdom"},
    "HYD": {"name": "Rajiv Gandhi International Airport", "city": "Hyderabad", "country": "India"},
    "DXB": {"name": "Dubai International Airport", "city": "Dubai", "country": "United Arab Emirates"},
}

# Single consistent demo itinerary. None of these values is connected to an airline.
DEMO_FLIGHTS = [
    {"flight_number": "DEMO101", "departure_local": "09:00", "arrival_local": "16:30", "fare_usd": 850, "available_seats": 12},
    {"flight_number": "DEMO202", "departure_local": "14:30", "arrival_local": "22:00", "fare_usd": 920, "available_seats": 8},
]
DEMO_BOOKINGS = {
    "DEMO123": {
        "booking_reference": "DEMO123",
        "status": "CONFIRMED (SIMULATED)",
        "passenger": "Demo Traveler",
        "flight_number": "DEMO101",
        "origin": "ORD",
        "destination": "IST",
        "cabin": "Economy",
        "seat": "18A",
        "checked_bags": 1,
    }
}

TOOL_NAMES = [
    "say_hello", "search_flights", "get_flight_status", "lookup_airport",
    "get_booking", "get_baggage_allowance", "get_available_seats",
    "get_miles_balance", "create_checkout_link",
]


def _airport(code: str) -> str:
    value = code.strip().upper()
    if len(value) != 3 or not value.isalpha():
        raise ValueError("Airport code must be three letters, e.g. ORD or IST")
    return value


def _date(value: str) -> str:
    try:
        return date.fromisoformat(value.strip()).isoformat()
    except ValueError as exc:
        raise ValueError("departure_date must be a valid YYYY-MM-DD date") from exc


def _flight(flight_number: str) -> dict:
    name = flight_number.strip().upper()
    for flight in DEMO_FLIGHTS:
        if flight["flight_number"] == name:
            return flight
    raise ValueError("Unknown demo flight. Try DEMO101 or DEMO202.")


# Existing OAuth discovery and JWT validation. No Railway/Descope changes required.
token_verifier = JWTVerifier(
    jwks_uri=DESCOPE_JWKS_URL,
    issuer=DESCOPE_ISSUER,
    audience=MCP_SERVER_URL,
    required_scopes=[REQUIRED_SCOPE],
)
auth_provider = RemoteAuthProvider(
    token_verifier=token_verifier,
    authorization_servers=[AnyHttpUrl(DESCOPE_ISSUER)],
    base_url=BASE_URL,
    scopes_supported=[REQUIRED_SCOPE],
)
mcp = FastMCP(name="Airline MCP Playground (Descope Protected)", auth=auth_provider)


def hello(name: str) -> str:
    return f"Hello {name}! This message is coming from my MCP server in the cloud."


@mcp.tool(auth=require_scopes(REQUIRED_SCOPE))
def say_hello(name: str) -> str:
    """Greet a user to confirm this protected MCP server is connected."""
    logger.info("say_hello invoked")
    return hello(name)


@mcp.tool(auth=require_scopes(REQUIRED_SCOPE))
def search_flights(origin: str, destination: str, departure_date: str) -> dict:
    """Search synthetic flights by airport codes and departure date YYYY-MM-DD.

    Returns sample fares and times, NEVER live flights or availability.
    """
    src, dst = _airport(origin), _airport(destination)
    day = _date(departure_date)
    if src == dst:
        raise ValueError("Origin and destination must be different")
    return {
        "origin": src, "destination": dst, "departure_date": day, "currency": "USD",
        "flights": [{**flight, "origin": src, "destination": dst, "departure_date": day} for flight in DEMO_FLIGHTS],
        "demo": True, "notice": "Synthetic options only; no live inventory or prices.",
    }


@mcp.tool(auth=require_scopes(REQUIRED_SCOPE))
def get_flight_status(flight_number: str) -> dict:
    """Get simulated status for DEMO101 or DEMO202. No real flight tracking."""
    flight = _flight(flight_number)
    return {
        "flight_number": flight["flight_number"],
        "status": "ON TIME (SIMULATED)" if flight["flight_number"] == "DEMO101" else "BOARDING (SIMULATED)",
        "departure_local": flight["departure_local"],
        "arrival_local": flight["arrival_local"],
        "demo": True,
    }


@mcp.tool(auth=require_scopes(REQUIRED_SCOPE))
def lookup_airport(airport_code: str) -> dict:
    """Look up demo airport metadata (ORD, IST, MKE, JFK, LHR, HYD, DXB)."""
    code = _airport(airport_code)
    if code not in AIRPORTS:
        return {"airport_code": code, "found": False, "supported_demo_codes": sorted(AIRPORTS), "demo": True}
    return {"airport_code": code, "found": True, **AIRPORTS[code], "demo": True}


@mcp.tool(auth=require_scopes(REQUIRED_SCOPE))
def get_booking(booking_reference: str) -> dict:
    """Look up a synthetic booking using reference DEMO123. No PII or real PNR lookup."""
    reference = booking_reference.strip().upper()
    booking = DEMO_BOOKINGS.get(reference)
    if not booking:
        return {"booking_reference": reference, "found": False, "hint": "Try DEMO123", "demo": True}
    return {**booking, "found": True, "demo": True}


@mcp.tool(auth=require_scopes(REQUIRED_SCOPE))
def get_baggage_allowance(cabin: str = "Economy") -> dict:
    """Return invented baggage policy for Economy or Business for demonstration."""
    normalized = cabin.strip().lower()
    if normalized not in {"economy", "business"}:
        raise ValueError("Supported demo cabins are Economy and Business")
    return {
        "cabin": normalized.title(),
        "carry_on": {"pieces": 1, "max_weight_kg": 8},
        "checked": {"pieces": 1 if normalized == "economy" else 2, "max_weight_kg_per_piece": 23 if normalized == "economy" else 32},
        "demo": True,
        "notice": "Invented teaching example, NOT an actual carrier baggage policy.",
    }


@mcp.tool(auth=require_scopes(REQUIRED_SCOPE))
def get_available_seats(flight_number: str, cabin: str = "Economy") -> dict:
    """Show fictional seat availability for DEMO101 or DEMO202."""
    flight = _flight(flight_number)
    normalized = cabin.strip().lower()
    if normalized not in {"economy", "business"}:
        raise ValueError("Supported demo cabins are Economy and Business")
    seats = (["18A", "18C", "19D", "20F"] if flight["flight_number"] == "DEMO101" else ["12A", "12B", "13F"])
    if normalized == "business":
        seats = ["2A", "2D"] if flight["flight_number"] == "DEMO101" else ["3A", "3D"]
    return {"flight_number": flight["flight_number"], "cabin": normalized.title(), "available_seats": seats, "demo": True}


@mcp.tool(auth=require_scopes(REQUIRED_SCOPE))
def get_miles_balance() -> dict:
    """Return the fixed balance of a fictional loyalty account, not the user's miles."""
    return {
        "account": "DEMO-LOYALTY-001",
        "program": "Airline Playground Rewards (fictional)",
        "balance_miles": 45000,
        "tier": "Explorer",
        "demo": True,
        "notice": "This balance is not connected to an authenticated person's real account.",
    }


@mcp.tool(auth=require_scopes(REQUIRED_SCOPE))
def create_checkout_link(flight_number: str, origin: str, destination: str, departure_date: str) -> dict:
    """Produce a link to a harmless DEMO checkout page. NO booking or payment occurs."""
    flight = _flight(flight_number)
    src, dst, day = _airport(origin), _airport(destination), _date(departure_date)
    if src == dst:
        raise ValueError("Origin and destination must be different")
    query = urlencode({"flight": flight["flight_number"], "origin": src, "destination": dst, "date": day})
    return {
        "checkout_url": f"{BASE_URL}/demo/checkout?{query}",
        "flight_number": flight["flight_number"], "origin": src, "destination": dst,
        "departure_date": day, "status": "NOT_BOOKED", "demo": True,
        "notice": "Demonstration URL only. It cannot reserve a flight or collect payment.",
    }


mcp_app = mcp.http_app(path="/mcp")
app = FastAPI(title="MCP + Descope + Poppy Playground", version="4.0.0", lifespan=mcp_app.lifespan)


@app.get("/", response_class=HTMLResponse)
async def homepage():
    items = "".join(f"<li><code>{escape(name)}</code></li>" for name in TOOL_NAMES)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MCP Airline Playground</title><style>
body{{font:16px system-ui,-apple-system,sans-serif;max-width:800px;margin:60px auto;padding:0 22px;color:#172b4d;line-height:1.6}}
a{{color:#155eef}}code{{background:#f2f4f7;padding:2px 6px;border-radius:4px}}</style></head><body>
<h1>MCP Airline Playground</h1><p><strong>9 protected MCP tools</strong> (8 mock airline tools + Hello World).</p>
<p>FastMCP + Railway + Descope OAuth. Streamable HTTP endpoint: <code>/mcp</code></p>
<h2>Tools</h2><ul>{items}</ul>
<p><strong>All airline data is fictional.</strong> No real booking, fares, inventory or charges.</p>
<ul><li><a href="/health">Health / tool list</a></li>
<li><a href="/hello?name=Kishore">Public hello REST example</a></li>
<li><a href="/.well-known/oauth-protected-resource/mcp">OAuth protected resource metadata</a></li>
<li><a href="/.well-known/poppy.json">Poppy placeholder discovery</a></li>
<li><a href="/docs">REST API docs</a></li></ul>
<p>MCP requests require a Descope bearer token with the <code>hello:read</code> scope.</p></body></html>"""


@app.get("/hello")
async def rest_hello(name: str = "World"):
    return {"result": hello(name)}


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "mcp-playground", "mcp_authentication": "required",
            "oauth_provider": "Descope", "required_scope": REQUIRED_SCOPE,
            "airline_tools": 8, "total_tools": len(TOOL_NAMES), "tools": TOOL_NAMES, "demo": True}


@app.get("/demo/checkout", response_class=HTMLResponse)
async def demo_checkout(flight: str = "", origin: str = "", destination: str = "", date: str = ""):
    # Static presentation only; no state modification, passenger input or payment.
    if flight not in {"DEMO101", "DEMO202"}:
        raise HTTPException(status_code=404, detail="Unknown demo flight")
    try:
        src, dst, day = _airport(origin), _airport(destination), _date(date)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Demo Checkout — No Purchase</title></head><body style="max-width:680px;margin:70px auto;font:18px system-ui">
<h1>Demo checkout handoff</h1><p><strong>This is not a real booking or payment page.</strong></p>
<p>{escape(flight)}: {escape(src)} → {escape(dst)} on {escape(day)}</p>
<p>No tickets reserved, no payment collected and no airline API called.</p></body></html>"""


@app.get("/.well-known/poppy.json")
async def poppy_discovery():
    # Preserved from existing project: discovery placeholder only, not full Poppy support.
    from urllib.parse import urlsplit
    return JSONResponse(content={"protocol_version": "1.0",
                                 "organization": {"name": "MCP Playground", "domain": urlsplit(BASE_URL).hostname},
                                 "web": {}})


app.mount("/", mcp_app)


if __name__ == "__main__":
    logger.info("Starting Airline MCP Playground: %s", MCP_SERVER_URL)
    logger.info("Descope issuer: %s | audience: %s", DESCOPE_ISSUER, MCP_SERVER_URL)
    logger.info("Protected MCP tools: %s", ", ".join(TOOL_NAMES))
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="info")
