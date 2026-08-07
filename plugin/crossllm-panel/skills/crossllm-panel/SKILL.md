---
name: crossllm-panel
description: Query OpenAI, Anthropic Claude, Google Gemini, Hugging Face, Kimi, Mistral, and Grok in parallel and synthesize their independent answers. Use for high-value decisions, adversarial review, fact or classification cross-checking, grant analysis, job classification, and tasks where the user explicitly requests multiple LLMs, a model panel, consensus, or CrossLLM_MCP. Do not use for simple questions where seven paid API calls would add little value.
---

# CrossLLM Panel

Use the `crossllm_mcp` tools to collect independent answers, then perform the final comparison in ChatGPT Work.

## Workflow

1. Call `list_panel_providers` before the first panel request in a conversation.
2. Tell the user which requested providers are not configured when that affects coverage.
3. Convert the user's task into a self-contained prompt. Preserve supplied facts, constraints, required output fields, and evaluation criteria.
4. Call `run_llm_panel` once. Omit `providers` to use all seven defaults; pass a subset only when the user requests it or cost constraints require it.
5. Wait for the complete tool result. Do not repeat successful calls merely because another provider failed.
6. Compare only results with `status: "ok"`. Treat missing or failed providers as missing evidence, never as disagreement.
7. Produce one answer that distinguishes:
   - consensus shared by most successful providers;
   - material disagreements and which evidence supports each side;
   - unique useful insights;
   - the final recommendation and confidence level.
8. Identify which provider produced a claim when attribution helps the user evaluate disagreement. Do not expose raw credentials, internal reasoning, or unnecessary provider metadata.

## Panel modes

- **Independent solution:** Give every model the same neutral task and synthesize the strongest supported answer.
- **Adversarial review:** Ask each model to find errors, risks, unsupported assumptions, and missing requirements.
- **Classification:** Require the same label schema and evidence from every model; report vote counts but use evidence rather than majority alone.
- **Decision panel:** Require recommendation, benefits, risks, assumptions, and disconfirming evidence from each model.

## Guardrails

- Do not claim that majority agreement proves truth.
- Prefer cited or user-supplied evidence over provider confidence or rhetoric.
- Do not ask providers to reveal chain-of-thought. Request concise conclusions and supporting evidence.
- Warn before running the full panel when the prompt is extremely large or repeated calls could be costly.
- Do not send secrets, credentials, or data the user has not authorized to all configured vendors.
- For confidential documents, confirm that cross-provider disclosure is acceptable before calling the panel.
- If fewer than two providers succeed, report that a meaningful cross-model comparison was not possible.
