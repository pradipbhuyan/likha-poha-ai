import base64
from openai import OpenAI
from app.config import settings

client = OpenAI(api_key=settings.OPENAI_API_KEY)


def generate_educational_image(prompt: str):
    educational_prompt = f"""
Create a clean educational illustration for a Grade 9 CBSE student.

Topic:
{prompt}

Style rules:
- clear textbook-style diagram
- simple labels
- child-friendly but not cartoonish
- no clutter
- high contrast
- suitable for science learning
- avoid tiny unreadable text
"""

    response = client.images.generate(
        model="gpt-image-1",
        prompt=educational_prompt,
        size="1024x1024",
        quality="medium",
    )

    image_base64 = response.data[0].b64_json

    return {
        "success": True,
        "image_base64": image_base64,
    }