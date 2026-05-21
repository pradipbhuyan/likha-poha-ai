try:
    import truststore
    truststore.inject_into_ssl()
except Exception:
    pass

from openai import OpenAI
from app.config import settings

client = OpenAI(api_key=settings.OPENAI_API_KEY)


def ask_llm(system_prompt: str, user_prompt: str) -> str:

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.4,
    )

    return response.output_text