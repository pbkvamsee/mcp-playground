# MCP Airline Playground — all 8 airline tools

Complete replacement for your existing `mcp-playground` GitHub repository files. Designed for your existing Railway domain and Descope/PingOne configuration.

## Files

- `server.py`: FastMCP server with 8 synthetic airline tools plus existing `say_hello`.
- `requirements.txt`: dependencies for Railway.

## Deployment

1. **Unzip**. Upload/replace `server.py` and `requirements.txt` in the **root** of `pbkvamsee/mcp-playground` on GitHub; optionally upload this README. Do not upload the ZIP directly as a deployable source file.
2. Commit to your deploy branch. Railway should build automatically.
3. Keep Railway start command `python server.py` and configured port `8080` (or let Railway inject `PORT`).
4. Existing Descope project ID, OAuth issuer, JWKS URL, `/mcp` resource audience, and `hello:read` scope are preserved. There is **no new Descope scope configuration** for this build.
5. Visit `https://mcp-playground-production.up.railway.app/health` to verify `total_tools: 9`.
6. Reconnect or refresh your existing Claude `test` MCP connector if necessary and ask it to list tools.

## Tools

| Tool | Test inputs | Notes |
| --- | --- | --- |
| `say_hello` | `name="Kishore"` | Original Hello World |
| `search_flights` | `origin="ORD", destination="IST", departure_date="2026-12-15"` | Returns fictional DEMO101/DEMO202 |
| `get_flight_status` | `flight_number="DEMO101"` | Simulated status |
| `lookup_airport` | `airport_code="ORD"` | 7 sample airports |
| `get_booking` | `booking_reference="DEMO123"` | Fictional passenger and reservation |
| `get_baggage_allowance` | `cabin="Economy"` | Fictional policy |
| `get_available_seats` | `flight_number="DEMO101", cabin="Economy"` | Fictional seats |
| `get_miles_balance` | (no parameters) | Fictional account with 45,000 miles |
| `create_checkout_link` | `flight_number="DEMO101", origin="ORD", destination="IST", departure_date="2026-12-15"` | Demo URL only; no reservation/payment |

## Suggested Claude test

> Use my test MCP server to find flights from ORD to IST on 2026-12-15. Look up ORD, check the status and available economy seats for DEMO101, retrieve booking DEMO123, check economy baggage rules and my **demo** loyalty balance, then create a **demo** checkout link for DEMO101. Use only MCP tools; show the results and identify all data as simulated.

## Security

- MCP endpoint stays OAuth-protected via `RemoteAuthProvider` and `JWTVerifier`.
- For this POC **all nine tools** require the existing `hello:read` scope. This is deliberately coarse-grained. Next iteration: split into `flights:read`, `bookings:read`, `profile:read`, and `bookings:write` and configure them in Descope.
- `/health`, `/`, `/hello`, and `/demo/checkout` are intentionally public informational/demo endpoints. No real personal data is exposed.
- All airline values are hardcoded demo fixtures. No external airline API, user lookup, payment, or booking writes.
- `/.well-known/poppy.json` is a basic placeholder only, **not** full Poppy support.
- Code syntax is checked locally; runtime interoperability with your Railway/Descope deployment needs validation after deployment.
