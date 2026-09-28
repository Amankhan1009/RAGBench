# RAGBench — Model-Independent AI & Provider Strategy

## 100% Model-Independent Provider Architecture
RAGBench LLM providers (`GroqProvider`, `OpenAIProvider`, `AnthropicProvider`, `GoogleProvider`) are 100% model-agnostic. No model names are hardcoded in dictionaries or restrictive schemas.

Users can supply **any present, unreleased, or future model identifier** supported by their cloud provider API key:
- **Groq:** `openai/gpt-oss-120b`, `deepseek-r1-distill-llama-70b`, or any Groq endpoint.
- **OpenAI:** `gpt-4o`, `gpt-4o-mini`, `o3-mini`, `o1`, `gpt-5.6-terra`, `luna-gpt-5.5`, `astra`, etc.
- **Anthropic:** `claude-3-5-sonnet`, `claude-3-7-sonnet`, `claude-4-haiku`, etc.
- **Google:** `gemini-1.5-pro`, `gemini-2.0-flash`, `gemini-3.0-ultra`, etc.

## Dynamic Token Pricing Calculation
Token costs are calculated dynamically via `calculate_token_cost(prompt_tokens, completion_tokens, input_cost_per_1k, output_cost_per_1k)` without hardcoded model price lookup tables.

All providers implement `BaseLLMProvider`:
- `generate(prompt, temperature, max_tokens) -> ProviderResponse`
- `generate_json(prompt, schema) -> ProviderResponse`
