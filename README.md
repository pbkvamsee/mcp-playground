# MCP + Poppy Playground

A minimal public-cloud Python application with **three interfaces in one Railway service**:

- **MCP**: `https://mcp-playground-production.up.railway.app/mcp`
- **Web + REST**: `https://mcp-playground-production.up.railway.app/` and `/hello?name=Kishore`
- **Poppy discovery**: `https://mcp-playground-production.up.railway.app/.well-known/poppy.json`

## Files

- `server.py` — FastAPI + FastMCP; same `hello()` logic for REST and MCP
- `requirements.txt` — Python dependencies
- `.gitignore` — excludes local/secret files

## Deploy to your existing Railway service

1. Extract this ZIP on your computer. **GitHub does not automatically extract a ZIP.**
2. Open your existing repository: <https://github.com/pbkvamsee/mcp-playground>.
3. Upload or replace the files in the **repository root**, then commit. Do not nest them under another folder.
4. Railway automatically deploys the new GitHub commit if connected.
5. Keep your Railway **start command** set to `python server.py`.
6. Keep Railway public networking routed to **port 8080**, as in your working deployment. The server uses `PORT` if Railway supplies it.
7. Once deployed, test the links above and `/health`, `/docs`.
8. Confirm Claude Code still sees the remote MCP tool with `claude mcp list`, then call `say_hello`.

## Local run (optional)

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
python server.py
```

Open <http://localhost:8080/>. MCP is at <http://localhost:8080/mcp>.

## Claude Code

If not already registered on a computer:

```bash
claude mcp add --transport http hello-world https://mcp-playground-production.up.railway.app/mcp
claude mcp list
```

## Changing hostnames

If you move to another Railway domain, set the Railway variable `PUBLIC_DOMAIN` to the hostname **without** `https://` (e.g., `myapp.up.railway.app`) so the Poppy metadata matches it.

## Scope / security

This example publishes **Poppy discovery only**. It does *not* implement Descope, OAuth, access tokens, agent identity, or delegated permissions. The `/hello` REST API and MCP tool are publicly reachable and unauthenticated. Never put private information or privileged operations here without adding proper authentication/authorization.

Opening `/mcp` in a normal browser may return an MCP HTTP media-type error. That is expected; the endpoint is intended for MCP clients.
