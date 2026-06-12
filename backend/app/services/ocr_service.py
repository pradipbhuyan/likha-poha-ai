import base64
from openai import OpenAI

from app.config import settings
from app.services.ssl_service import enable_system_truststore

enable_system_truststore()

# OCR model preference order: nano first (cheapest), mini as fallback
_OCR_MODELS = ["gpt-4.1-nano", "gpt-4.1-mini"]

_PROMPT = """
Extract all readable textbook text from this image.
Preserve headings, examples, formulas, question numbers, and tables where possible.
Return clean plain text only.
"""


def _get_client() -> OpenAI:
    """Return an OpenAI client using the effective API key (DB key if set, else env)."""
    try:
        from app.services.openai_service import get_effective_settings  # noqa: PLC0415
        api_key = get_effective_settings().get("api_key") or settings.OPENAI_API_KEY
    except Exception:
        api_key = settings.OPENAI_API_KEY
    return OpenAI(api_key=api_key)


def extract_text_from_image_bytes(image_bytes: bytes) -> str:
    """
    OCR readable textbook/question text from image bytes using a vision model.

    Uses the same API key as all other LLM calls (DB key via Admin Control,
    falling back to the Render OPENAI_API_KEY env var).
    Tries gpt-4.1-nano first; falls back to gpt-4.1-mini if the project
    does not have nano access.
    """
    client = _get_client()
    image_base64 = base64.b64encode(image_bytes).decode("utf-8")

    last_error: Exception | None = None
    for model in _OCR_MODELS:
        try:
            response = client.responses.create(
                model=model,
                input=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "input_text",
                                "text": _PROMPT,
                            },
                            {
                                "type": "input_image",
                                "image_url": f"data:image/jpeg;base64,{image_base64}",
                            },
                        ],
                    }
                ],
            )
            return response.output_text
        except Exception as exc:
            last_error = exc
            # Only retry with next model on access/not-found errors
            err_str = str(exc).lower()
            if "model_not_found" in err_str or "does not have access" in err_str or "403" in err_str:
                continue
            raise  # re-raise unrelated errors immediately

    raise RuntimeError(f"OCR failed on all models: {last_error}")
