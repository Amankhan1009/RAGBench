# RAGBench — Model-Independent AI & Provider Strategy

## Model-Independent Provider Architecture
RAGBench providers are model-agnostic and decoupled from hardcoded model names. 
Users can specify any valid model identifier supported by their API key/provider:
- **Groq:** `openai/gpt-oss-120b`, `llama-3.3-70b-specdec`, or any Groq endpoint.
- **OpenAI:** `gpt-4o`, `gpt-4o-mini`, `o3-mini`, `o1`, `gpt-4.5-turbo`, or custom fine-tunes.
- **Anthropic:** `claude-3-5-sonnet-20241022`, `claude-3-7-sonnet`, `claude-3-5-haiku`, etc.
- **Google:** `gemini-1.5-pro`, `gemini-2.0-flash`, `gemini-2.5-pro`, etc.

All providers implement `BaseLLMProvider`:
- `generate(prompt, temperature, max_tokens) -> ProviderResponse`
- `generate_json(prompt, schema) -> ProviderResponse`
