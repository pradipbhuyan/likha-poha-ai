import base64
from openai import OpenAI
from app.config import settings
from app.services.usage_service import log_ai_usage
from app.services.usage_service import log_ai_usage, enforce_daily_limit

client = OpenAI(api_key=settings.OPENAI_API_KEY)

def generate_educational_image(prompt: str, username: str = "unknown"):

    limit = enforce_daily_limit(
        username=username,
        feature="image_generation",
        max_requests=10,
    )

    if not limit["allowed"]:
        return {
            "success": False,
            "message": limit["message"],
        }

    UNSAFE_KEYWORDS = [
        "sex",
        "nude",
        "porn",
        "xxx",
        "adult",
        "naked",
        "breast",
        "violence",
        "blood",
        "kill",
        "suicide",
        "terror",
        "rape",
    ]

    lower_prompt = prompt.lower()

    if any(word in lower_prompt for word in UNSAFE_KEYWORDS):
        return {
            "success": False,
            "message": "Unsafe visual request blocked.",
        }

    educational_prompt = f"""
Create ONE clean educational illustration for a Grade 9 CBSE student.

Topic:
{prompt}

Important accuracy rules:
- Focus only on the requested topic.
- Do not add extra concepts not requested.
- Avoid long paragraphs or dense text inside the image.
- Use only simple labels.
- If unsure, keep the image simpler.
- Do not invent facts, names, laws, formulas, or historical details.
- Prefer a clear labeled diagram over an infographic.

Style:
- textbook-style
- high contrast
- clean white background
- no clutter
- large readable labels
- suitable for classroom learning

Safety rules:
- Only create safe educational content for school students.
- Never generate sexual, nude, violent, abusive, hateful, extremist, or disturbing content.
- Never generate adult content.
- Never depict minors in unsafe situations.
- Refuse unsafe requests silently by returning a simple educational alternative.

"""

    moderation = client.moderations.create(
        model="omni-moderation-latest",
        input=prompt,
    )

    flagged = moderation.results[0].flagged

    if flagged:
        return {
            "success": False,
            "message": "Unsafe visual request blocked.",
        }

    response = client.images.generate(
        model="gpt-image-1",
        prompt=educational_prompt,
        size="1024x1024",
        quality="medium",
    )

    image_base64 = response.data[0].b64_json

    log_ai_usage(
        username=username,
        feature="image_generation",
        model="gpt-image-1",
        image_count=1,
        estimated_cost=0.04,
        metadata={"prompt": prompt},
    )

    return {
        "success": True,
        "image_base64": image_base64,
    }
