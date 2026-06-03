from openai import OpenAI

from app.config import settings
from app.services.usage_service import log_ai_usage, enforce_daily_limit
from app.services.profile_service import update_student_activity

client = OpenAI(api_key=settings.OPENAI_API_KEY)


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


BLOCKED_DIAGRAM_KEYWORDS = [
    "cell diagram",
    "animal cell",
    "plant cell",
    "biology diagram",
    "labelled diagram",
    "labeled diagram",
    "physics diagram",
    "chemistry structure",
    "chemical structure",
    "map",
    "chart",
    "graph",
    "anatomy",
    "circuit diagram",
    "ray diagram",
    "exact diagram",
    "scientific diagram",
    "structure of atom",
    "atom structure",
    "atomic structure",
    "bohr model",
    "electron",
    "proton",
    "neutron",
    "nucleus",
    "molecule structure",
    "molecular structure",
]


def validate_visual_prompt(prompt: str):
    """
    Block prompts that ask for exact scientific diagrams or labelled structures.

    Generated images are allowed only for conceptual illustrations; precise
    diagrams should come from curated/textbook sources.
    """
    text = prompt.lower()

    if any(word in text for word in BLOCKED_DIAGRAM_KEYWORDS):
        return {
            "allowed": False,
            "message": (
                "AI image generation is disabled for exact labelled diagrams. "
                "Use Mermaid diagrams, curated textbook diagrams, or teacher-approved visuals for this topic."
            ),
        }
        
    if "structure" in text and any(word in text for word in [
            "atom",
            "cell",
            "molecule",
            "heart",
            "eye",
            "brain",
            "plant",
            "leaf",
            "circuit",
        ]):
            return {
                "allowed": False,
                "message": (
                    "AI image generation is disabled for exact scientific structures. "
                    "Use Mermaid diagrams, curated textbook diagrams, or teacher-approved visuals for this topic."
                ),
            }

    return {
        "allowed": True,
        "message": "",
    }


def generate_educational_image(prompt: str, username: str = "unknown"):
    """
    Generate a safe conceptual education image and log image usage.

    The function enforces daily limits, blocks unsafe requests, and rejects
    diagram prompts where hallucinated labels could mislead students.
    """
    limit = enforce_daily_limit(
        username=username,
        feature="image_generation",
        max_requests=5,
    )

    if not limit["allowed"]:
        return {
            "success": False,
            "message": limit["message"],
        }

    lower_prompt = prompt.lower()

    if any(word in lower_prompt for word in UNSAFE_KEYWORDS):
        return {
            "success": False,
            "message": "Unsafe visual request blocked.",
        }

    visual_validation = validate_visual_prompt(prompt)

    if not visual_validation["allowed"]:
        return {
            "success": False,
            "message": visual_validation["message"],
        }

    educational_prompt = f"""
Create ONE clean conceptual educational illustration for a Grade 9 CBSE student.

Topic:
{prompt}

Important accuracy rules:
- Use this only as a conceptual illustration, not as an exact scientific diagram.
- Do not create detailed labelled biology, chemistry, physics, map, graph, circuit, or anatomy diagrams.
- Do not add extra concepts not requested.
- Avoid long paragraphs or dense text inside the image.
- Use minimal text.
- If unsure, keep the image simple and symbolic.
- Do not invent facts, names, laws, formulas, or historical details.

Style:
- textbook-inspired conceptual illustration
- high contrast
- clean white background
- no clutter
- classroom-friendly
- suitable for school learning

Safety rules:
- Only create safe educational content for school students.
- Never generate sexual, nude, violent, abusive, hateful, extremist, or disturbing content.
- Never generate adult content.
- Never depict minors in unsafe situations.
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

    update_student_activity(
        username=username,
        activity_type="visual_generated",
    )

    return {
        "success": True,
        "image_base64": image_base64,
    }
