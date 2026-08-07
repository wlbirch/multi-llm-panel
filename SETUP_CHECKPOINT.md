# CrossLLM Panel setup checkpoint

Last updated: 2026-08-07 (America/Chicago)

## Objective

Connect one private ChatGPT Work MCP plugin to seven LLM providers in parallel: OpenAI, Anthropic/Claude, Gemini, Hugging Face, Kimi/Moonshot, Mistral, and Grok/xAI.

## Project locations

- Local repository: `C:\Users\Analytics Laptop\Documents\Chat Work Projects\LLM Panels\multi-llm-panel`
- Private GitHub repository: `https://github.com/wlbirch/multi-llm-panel`
- Render MCP service: `https://crossllm-mcp.onrender.com/mcp`
- Health check: `https://crossllm-mcp.onrender.com/health`
- Auth0 tenant: `https://dev-5phm4adx1gab23y0.us.auth0.com`
- Auth0 API identifier/audience: `https://crossllm-mcp.onrender.com/mcp`
- ChatGPT DCR client ID: `tpc_iKn5ici4rntzLKwybBVh6b`

## Completed

- Seven-provider concurrent MCP service built, tested, and deployed on Render.
- Private plugin/skill bundle created and pointed at the production Render URL.
- Local test suite passes (8 tests).
- Render health and OAuth protected-resource metadata work.
- Auth0 API uses RS256 and has a per-application client grant for ChatGPT.
- Auth0 Dynamic Client Registration is enabled temporarily.
- Google login connection is promoted to domain level for the third-party ChatGPT client.
- ChatGPT registered the OAuth client and shows the CrossLLM Panel connection.
- JWT verification enforces Auth0 signature, issuer, audience, expiration, and exact ChatGPT client ID.
- Auth0 Post Login Action `Add CrossLLM Panel Scope` is deployed and attached to the Post Login trigger.
- No provider API keys have been entered into Render, Auth0, GitHub, ChatGPT, or this conversation.

## Current unresolved issue

ChatGPT's plugin Refresh still fails and displays no actions. Render shows this sequence:

1. `POST /mcp` -> `401 Unauthorized` (expected discovery challenge)
2. `GET /.well-known/oauth-protected-resource/mcp` -> `200 OK`
3. JWT verifier logs `Accepted OAuth access token client_id=tpc_iKn5ici4rntzLKwybBVh6b ...`
4. Authenticated `POST /mcp` -> `403 Forbidden`

This proves the signed token, issuer, audience, and client allowlist pass. The remaining failure is the required `run:panel` scope. The full diagnostic line was truncated in the screenshot, so the exact scopes Auth0 issued were not captured.

## Active Auth0 Action

```javascript
exports.onExecutePostLogin = async (event, api) => {
  const expectedClientId = "tpc_iKn5ici4rntzLKwybBVh6b";

  if (event.client.client_id === expectedClientId) {
    api.accessToken.addScope("run:panel");
  }
};
```

The repository copy is `auth0/actions/add_crossllm_scope.js`.

## Repository/deployment state

- Current repository HEAD: `672a6d4` (`Scope Auth0 action to ChatGPT client`)
- Last server-affecting diagnostic commit: `c660087` (`Log verified OAuth scope names`)
- Render auto-deploy appears disabled; use Manual Deploy when server files change.
- Render currently requires `run:panel` and allowlists the exact ChatGPT client ID.

## Resume here

1. In Auth0 Monitoring > Logs, trigger a fresh ChatGPT account reconnect and inspect the newest Successful Login event's Action Details. Confirm `Add CrossLLM Panel Scope` executed without error.
2. In Render Logs, search for `Accepted OAuth access token` and copy the complete line, including `scopes=[...]`.
3. If `run:panel` is absent, verify the deployed Action version and trigger binding, then force Auth0 to issue a genuinely new access token for the existing connector client. Do not delete the plugin or register a different client unless the server and Action allowlists are updated together.
4. When ChatGPT displays `list_panel_providers` and `run_llm_panel`, disable Auth0 DCR. Keep the Google connection promoted to domain level.
5. Add the seven provider keys only in Render's Environment/secret settings and redeploy.
6. Run `list_panel_providers`, then a low-cost one-provider test, then the full seven-provider panel.
7. Enable Render auto-deploy after authentication is stable.

## Safety constraints

- Never paste provider keys, OAuth secrets, access tokens, or refresh tokens into chat, GitHub, or Auth0 logs.
- Do not weaken issuer, audience, expiration, client-ID, or `run:panel` authorization checks to bypass the `403`.
- Disable open DCR after the existing ChatGPT connector works.
