# MCP Playground — Descope login required for MCP

This version **requires Descope OAuth tokens for all MCP traffic** at `/mcp`. The public `/hello` REST demonstration and website remain reachable without authentication. The separately protected `/api/hello` retains its JWT + introspection sample, which requires confidential client credentials.

## 1. Descope setup (before deploying)

In Descope project `P3ML27ocPWZS6vulRanlFpjFkO20`:

1. Under Agentic Identity Hub > MCP Servers (or Resources), register the existing MCP URL `https://mcp-playground-production.up.railway.app/mcp` according to the Descope console. **Resource identifier / token audience must match** `https://mcp-playground-production.up.railway.app`, because this project uses that HTTPS origin for the OAuth resource metadata and JWT audience. If Descope requires the MCP URL as its Resource identifier instead, update `RESOURCE_ID` in server.py and the protected resource metadata to the **exact same value** before testing.
2. Add permission `hello:read` and consent text `Use the Hello World tool`.
3. Configure an interactive user-consent/login flow.
4. Under Project Settings > OIDC > Client Registration, enable **CIMD** and allow Anthropic's Claude published client metadata domain as an approved domain; or enable DCR and choose **Register automatically** in Claude. Verify what the project's issuer actually publishes in OAuth discovery.
5. From the Descope authorization server discovery metadata, copy the **exact `jwks_uri`**. Do not guess a URL.

## 2. Railway

Upload the extracted project files to GitHub, overwriting the old versions. Set these Railway service variables:

- `DESCOPE_JWKS_URL` = the exact `jwks_uri` from Descope's discovery (required; deployment fails closed if omitted)
- `PUBLIC_DOMAIN` = `mcp-playground-production.up.railway.app`
- `DESCOPE_PROJECT_ID` = `P3ML27ocPWZS6vulRanlFpjFkO20`
- `DESCOPE_ISSUER` = `https://api.descope.com/v1/apps/P3ML27ocPWZS6vulRanlFpjFkO20`
- `DESCOPE_CLIENT_ID` and `DESCOPE_CLIENT_SECRET` = confidential client allowed to introspect tokens (only necessary for the **separate** `/api/hello` REST demo)

Keep Railway start command `python server.py`. Keep Railway public Networking target set to the actual `PORT` shown in deployment logs (earlier: 8080).

## 3. Verify BEFORE asking Claude to connect

```bash
curl -i https://mcp-playground-production.up.railway.app/mcp
```

Expected: HTTP 401 and `WWW-Authenticate: Bearer ...` (not 406, 502, or 200). Test authenticated OAuth metadata:

```bash
curl -i https://mcp-playground-production.up.railway.app/.well-known/oauth-protected-resource
curl -i https://mcp-playground-production.up.railway.app/.well-known/poppy.json
```

Then in Claude Desktop: add a **new** custom connector URL `https://mcp-playground-production.up.railway.app/mcp`, choose **Sign in now** and **Use Claude's published identity** (when CIMD enabled), or **Register automatically** (when DCR enabled). Complete Descope login/consent. Note that existing unauthenticated Claude Code config will need reauthentication.

## Security boundaries

- The MCP transport rejects missing, expired, malformed, wrong-audience, wrong-issuer or missing-scope JWTs through `RemoteAuthProvider` + `JWTVerifier`.
- This is **not** proof of cryptographic agent request identity (e.g. signed Poppy Session), DPoP, or immediate OAuth revocation. The FastMCP JWT verifier checks JWTs locally and may honor a revoked token until expiry. For live revocation, implement and test a compatible Descope introspection/token verification layer.
- `/.well-known` metadata and `/hello` intentionally remain public.
- Do not commit secrets.

References: https://gofastmcp.com/docs/servers/auth/remote-oauth and https://docs.descope.com/agentic-identity-hub/core-components/mcp-servers
