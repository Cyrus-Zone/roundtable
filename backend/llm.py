"""LLM call layer — thin wrapper around LiteLLM."""
import litellm


def call_llm(
    model: str,
    messages: list[dict],
    api_key: str,
    base_url: str | None = None,
    temperature: float = 0.7,
) -> str:
    """Call any LLM via LiteLLM (OpenAI-compatible format)."""
    litellm.drop_params = True
    response = litellm.completion(
        model=model,
        messages=messages,
        api_key=api_key,
        base_url=base_url,
        temperature=temperature,
    )
    return response.choices[0].message.content or ""


def count_tokens(text: str, model: str) -> int:
    """Estimate token count for a string."""
    try:
        return litellm.token_counter(model=model, text=text) or 0
    except Exception:
        # Fallback: rough character-to-token ratio
        return len(text) // 4
