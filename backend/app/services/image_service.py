from openai import OpenAI

from app.config import settings
from app.services.ssl_service import enable_system_truststore
from app.services.usage_service import log_ai_usage, enforce_daily_limit
from app.services.profile_service import update_student_activity

enable_system_truststore()

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


def validate_visual_context(subject: str = "", mode: str = ""):
    """
    Allow AI-generated conceptual visuals only for Science and Maths contexts.

    Other subjects should use more reliable learning tools such as passages,
    vocabulary maps, examples, or practice questions instead of decorative
    generated images.
    """
    subject_text = (subject or "").strip().lower()

    if "science" in subject_text or "math" in subject_text:
        return {
            "allowed": True,
            "message": "",
        }

    return {
        "allowed": False,
        "message": (
            "Visual generation is available only for Science and Maths lessons. "
            "For language and other subjects, use practice questions or examples instead."
        ),
    }


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


def build_subject_visual_rules(subject: str = "") -> str:
    """Return subject-specific image rules to reduce misleading generated visuals."""
    subject_text = (subject or "").strip().lower()

    if "math" in subject_text:
        return """
Maths visual rules:
- Do not create a formula poster.
- Do not make large standalone equations the main visual.
- Prefer a visual model: number line, fraction bar, area model, grid, coordinate plane, geometry sketch, or simple graph.
- Use little or no text inside the image.
- If text is needed, use only short labels like 0, 1, Half, Point A, x-axis, y-axis.
- Show relationships spatially instead of writing explanations inside the image.
"""

    if "science" in subject_text:
        return """
Science visual rules:
- Create a conceptual scene or simple process illustration.
- Avoid exact labelled scientific diagrams unless the prompt explicitly asks for a simple concept visual.
- Prefer useful learning visuals: process flow, cause-effect scene, experiment setup, cycle, sequence, classification tree, or real-life example.
- Avoid decorative pictures that do not explain a concept.
- Do not create dense textbook pages or posters.
- Use little or no text inside the image.
"""

    return ""


def generate_educational_image(
    prompt: str,
    username: str = "unknown",
    grade: str = "",
    subject: str = "",
    chapter: str = "",
    mode: str = "CBSE",
):
    """
    Generate a safe conceptual education image and log image usage.

    The function enforces daily limits, blocks unsafe requests, and rejects
    diagram prompts where hallucinated labels could mislead students.
    """
    context_validation = validate_visual_context(
        subject=subject,
        mode=mode,
    )

    if not context_validation["allowed"]:
        return {
            "success": False,
            "message": context_validation["message"],
        }

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
	Create ONE clean conceptual educational illustration for the grade and topic requested by the user.

Topic:
{prompt}

Lesson context:
- Grade: {grade if grade else "Not provided"}
- Mode: {mode if mode else "CBSE"}
- Subject: {subject if subject else "Not provided"}
- Chapter: {chapter if chapter else "Not provided"}

{build_subject_visual_rules(subject)}

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
        metadata={
            "prompt": prompt,
            "grade": grade,
            "mode": mode,
            "subject": subject,
            "chapter": chapter,
        },
    )

    update_student_activity(
        username=username,
        activity_type="visual_generated",
    )

    return {
        "success": True,
        "image_base64": image_base64,
    }
