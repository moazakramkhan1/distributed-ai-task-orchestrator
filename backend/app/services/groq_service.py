from groq import Groq, APIError, APIConnectionError, RateLimitError

from app.core.config import settings

_PROMPT_SYSTEM = (
    "You are an AI system that analyzes spatial, review, or operational text. "
    "Read the input and produce:\n"
    "1. A short summary\n"
    "2. Key issues or signals\n"
    "3. Recommended next action"
)


def analyze_text(input_text: str) -> str:
    if not settings.GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY is not configured")

    client = Groq(api_key=settings.GROQ_API_KEY)

    try:
        response = client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[
                {"role": "system", "content": _PROMPT_SYSTEM},
                {"role": "user", "content": input_text},
            ],
            max_tokens=512,
            temperature=0.3,
        )
        return response.choices[0].message.content.strip()
    except (APIError, APIConnectionError, RateLimitError) as exc:
        raise RuntimeError(f"Groq API error: {exc}") from exc
