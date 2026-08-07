# CrossLLM Panel for ChatGPT Work

CrossLLM Panel exposes one authenticated MCP tool that submits the same task to seven independent LLM providers in parallel. ChatGPT Work receives all successful answers and synthesizes the consensus, disagreements, and strongest supported conclusion.

## Provider map

| Panel name | Credential | Default model |
| --- | --- | --- |
| OpenAI | `OPENAI_API_KEY` | `gpt-5.6-terra` |
| Anthropic | `ANTHROPIC_API_KEY` | `claude-sonnet-5` |
| Gemini | `GEMINI_API_KEY` | `gemini-3.6-flash` |
| Hugging Face | `HUGGINGFACE_API_KEY` | Configurable Inference Provider model |
| Kimi | `KIMI_API_KEY` | `kimi-k3` |
| Mistral | `MISTRAL_API_KEY` | `mistral-large-latest` |
| Grok/xAI | `XAI_API_KEY` | `grok-4.5` |

`LLamaCoLab` and `QwenCoL` are supported as optional OpenAI-compatible endpoints. `LlamaParse` is reserved for document preprocessing and is not counted as an LLM panel member.

## Local setup

1. Create a virtual environment: `python -m venv .venv`.
2. Activate it on Windows: `.venv\Scripts\Activate.ps1`.
3. Install dependencies: `python -m pip install -r requirements-dev.txt`.
4. Copy `.env.example` to `.env` and keep `AUTH_MODE=dev` locally.
5. Add provider keys to `.env`. Never commit `.env`.
6. Start the endpoint: `python -m server.app`.
7. Test `http://localhost:8788/mcp` with MCP Inspector.

## Secure production setup

1. Deploy the bootstrap Blueprint as a free Docker web service. It starts in `AUTH_MODE=dev` with no provider credentials so you can obtain the permanent Render URL without exposing paid APIs.
2. Create an Auth0 API whose identifier exactly matches the deployed MCP resource URL (`https://crossllm-mcp.onrender.com/mcp`).
3. Set User-Delegated Application Access to per-app authorization and grant ChatGPT's dynamically registered client access to the API. Set `JWT_CLIENT_IDS` to that client's `tpc_...` ID so tokens from other OAuth clients are rejected.
4. Enable Auth0 Dynamic Client Registration temporarily so ChatGPT can register its connector client, then disable open registration after the connection is established.
5. Deploy the production OAuth settings in `render.yaml` without provider credentials and verify protected-resource discovery.
6. Connect the deployed `/mcp` endpoint in ChatGPT Work Developer Mode using OAuth.
7. Disable open Dynamic Client Registration in Auth0 after ChatGPT has registered its connector client.
8. Add the seven provider credentials in Render's secret environment settings and redeploy.
9. Validate and upload/install the plugin after the authenticated panel test succeeds.

## Cost and safety controls

- Calls run concurrently and partial failures do not discard successful answers.
- Output length, timeouts, provider selection, and concurrency are capped by environment variables.
- The service never returns or logs provider keys.
- Use provider-side budgets and rate limits before enabling the full seven-provider panel.
- Production mode refuses to start without OAuth issuer and audience settings.
