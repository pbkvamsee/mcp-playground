# MCP + Poppy + Descope OAuth playground

GitHub: `pbkvamsee/mcp-playground`  
Railway: `https://mcp-playground-production.up.railway.app`

This is a **POC**, not a fully compliant, production-ready Poppy agent implementation.

## What it provides

| Path | Purpose | Auth |
|---|---|---|
| `/` | Browser homepage | Public |
| `/health` | Railway health | Public |
| `/hello?name=Kishore` | Browser demo API | Public |
| `/mcp` | Existing FastMCP `say_hello` tool (Claude Code) | Public |
| `/.well-known/poppy.json` | Poppy 1.0 discovery with Descope issuer and API | Public |
| `/.well-known/oauth-protected-resource` | OAuth resource metadata | Public |
| `/openapi.json`, `/docs` | OpenAPI spec / Swagger | Public docs |
| `/api/hello?name=Kishore` | OAuth-protected REST API | Descope `hello:read` |

## Deploy to Railway

1. Extract the ZIP. Commit its **files**, not the ZIP itself, to the root of your existing GitHub repository, replacing the existing `server.py` and `requirements.txt`.
2. In Railway, keep **start command** `python server.py` and the public domain's target **port 8080** as previously configured.
3. Railway redeploys automatically if GitHub auto-deploy is enabled.
4. Test `/health`, `/hello?name=Kishore`, `/.well-known/poppy.json`, `/.well-known/oauth-protected-resource` and `/mcp` with Claude Code.

## Descope Console setup REQUIRED

Your uploaded guide names project `P3ML27ocPWZS6vulRanlFpjFkO20` and issuer `https://api.descope.com/v1/apps/P3ML27ocPWZS6vulRanlFpjFkO20`. **Confirm this exact issuer against the discovery document in your Descope account.** Do not use another project or secret in public Git.

1. In Descope create an **API Resource** with identifier exactly:
   `https://mcp-playground-production.up.railway.app` (no trailing slash).
2. Add scope **`hello:read`** with consent text such as "Read a personalized Hello World response." Register an **Inbound App / authorized client** and a policy permitting this Resource + scope. Enable the customer-facing authorization grant flow needed by your agent (e.g. Device Authorization). Descope Console options may differ by tenant.
3. Verify the issuer's discovery metadata:
   `https://api.descope.com/v1/apps/P3ML27ocPWZS6vulRanlFpjFkO20/.well-known/openid-configuration`
   Copy the **jwks_uri** from that response. The signing-key endpoint must be HTTPS and match your issuer. Confirm the issuer and that Descope's authorization metadata supports the grant/client authentication your agent will use.
4. In Railway **service -> Variables**, add (DO NOT commit actual values):
   - `DESCOPE_JWKS_URL` (the verified `jwks_uri` from #3)
   - `DESCOPE_CLIENT_ID` and `DESCOPE_CLIENT_SECRET` (credentials for a confidential client permitted to perform RFC 7662 token introspection). Verify your Descope setup accepts HTTP Basic for introspection; if it requires another method, adapt the HTTP request accordingly before enabling access.
   - `DESCOPE_PROJECT_ID` if different from the included example.
   - `DESCOPE_ISSUER` if the Descope metadata supplies a different issuer; keep discovery metadata and your token validation consistent.
5. Redeploy and request a **user-delegated access token** using the approved client/grant with Resource `https://mcp-playground-production.up.railway.app` and scope `hello:read`. Descope must issue a signed JWT with this exact `aud`, the expected `iss`, and an expiry.
6. Test with token (never paste a token into a public chat):

   ```bash
   curl -i -H "Authorization: Bearer $ACCESS_TOKEN" \
     'https://mcp-playground-production.up.railway.app/api/hello?name=Kishore'
   ```

   Without a token: HTTP 401. Valid signature/issuer/audience/scope and active introspection: HTTP 200. Missing scope: HTTP 403. Missing server configuration or unavailable introspection: HTTP 503 (fail closed).

## Important security / protocol limitations

- **Poppy-Session is not verified.** No agent identity, session claims, actor-vs-user provenance, or delegated agent rights are established. This stateless `/api/hello` endpoint makes authorization decisions using OAuth access-token claims only. Do not add session-based actions, account mutations, or risk-sensitive operations without verifying delegated Poppy-Session JWTs and client metadata per the Poppy spec.
- No DPoP proof verification or sender-constrained token support. Only use bearer tokens whose issuer is configured to allow this model. Do not accept DPoP-bound tokens as bearer tokens without proof validation.
- MCP `/mcp` and public REST `/hello` remain unauthenticated. They are harmless demo functions **only**. The Descope protected REST route is distinct.
- The Poppy 1.0 spec requires **two-way issuer/domain linkage** (issuer metadata listing your domain), beyond publishing a resource document. Check that your configured Descope issuer supports the necessary metadata and that the validator passes; don't assume it will pass from this code alone.
- JWKS URL must be trusted config from your issuer; never resolve it from the token's `jku` or `x5u` header.
- Introspection uses a confidential app client and checks `active=true`; verify the credentials and authentication method for your Descope tenant. We fail closed when they are missing or introspection fails.
- This POC does not include login UX, token acquisition, refresh, per-agent authorization, or Poppy agent client registration.

## Helpful references

- https://personalagentprotocol.org/docs/1.0/spec
- https://docs.descope.com/identity-federation/inbound-apps/authorization-server
- https://docs.descope.com/identity-federation/inbound-apps/developing-apis
- https://github.com/adewale/pda

### Validate Poppy metadata

The `adewale/pda` reference agent has a validator. On Node.js 24+:

```bash
git clone https://github.com/adewale/pda.git
cd pda
npm install --legacy-peer-deps
npm run validate -- mcp-playground-production.up.railway.app
```

The validator may flag unsupported Descope issuer metadata (such as `poppy_domains`) until you configure the issuer accordingly. This is **not** a sign that the REST JWT validation is already integrated end-to-end.
