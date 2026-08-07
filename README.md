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
2. Create an Auth0 API whose identifier exactly matches the deployed MCP resource URL (`https://YOUR-SERVICE.onrender.com/mcp`).
3. Enable Auth0 Client ID Metadata Document registration and configure user-delegated access.
4. In Render's secret environment settings, add all provider credentials plus `AUTH0_ISSUER`, `JWT_AUDIENCES`, and `RESOURCE_SERVER_URL`.
5. Change `AUTH_MODE` from `dev` to `oauth` and redeploy. Do not add provider keys until this OAuth change is ready to deploy.
6. Connect the deployed `/mcp` endpoint in ChatGPT Work Developer Mode using OAuth.
7. Replace the staging URL in `plugin/crossllm-panel/.mcp.json`, validate the plugin, and upload/install it.

## Cost and safety controls

- Calls run concurrently and partial failures do not discard successful answers.
- Output length, timeouts, provider selection, and concurrency are capped by environment variables.
- The service never returns or logs provider keys.
- Use provider-side budgets and rate limits before enabling the full seven-provider panel.
- Production mode refuses to start without OAuth issuer and audience settings.
