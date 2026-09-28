# RAGBench — AI Model & Provider Strategy
## Provider Architecture
All providers implement `BaseLLMProvider`:
- `generate(prompt, temperature, max_tokens) -> ProviderResponse`
- `generate_json(prompt, schema) -> ProviderResponse`
## Provider Roster
1. **Groq:** Primary fast model (`openai/gpt-oss-120b`)
2. **OpenAI:** Standard benchmark judge (`gpt-4o`, `gpt-4o-mini`)
3. **Anthropic:** Reasoning judge (`claude-3-5-sonnet`)
4. **Google:** Multimodal/Large context judge (`gemini-1.5-pro`)
