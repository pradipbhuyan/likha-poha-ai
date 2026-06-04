import base64
from openai import OpenAI

from app.config import settings
from app.services.ssl_service import enable_system_truststore

enable_system_truststore()

client = OpenAI(api_key=settings.OPENAI_API_KEY)


def extract_text_from_image_bytes(image_bytes: bytes) -> str:
    """
    OCR readable textbook/question text from image bytes using a vision model.

    The prompt asks for clean plain text only so callers can reuse the result for
    RAG upload, SOF grouping, or Ask Doubt context.
    """
    image_base64 = base64.b64encode(image_bytes).decode("utf-8")

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": """
Extract all readable textbook text from this image.
Preserve headings, examples, formulas, question numbers, and tables where possible.
Return clean plain text only.
"""
                    },
                    {
                        "type": "input_image",
                        "image_url": f"data:image/jpeg;base64,{image_base64}"
                    }
                ]
            }
        ]
    )

    return response.output_text
