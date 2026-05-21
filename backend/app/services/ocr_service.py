import base64
from openai import OpenAI

from app.config import settings

try:
    import truststore
    truststore.inject_into_ssl()
except Exception:
    pass


client = OpenAI(api_key=settings.OPENAI_API_KEY)


def extract_text_from_image_bytes(image_bytes: bytes) -> str:
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