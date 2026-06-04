from app.services.openai_service import (
    DEFAULT_TEXT_MODEL,
    GPT5_MINI_TEXT_MODEL,
    GPT5_TEXT_MODEL,
)


DEFAULT_MODEL_PREFERENCE = "default"
SUPPORTED_MODEL_PREFERENCES = {
    DEFAULT_MODEL_PREFERENCE,
    GPT5_TEXT_MODEL,
    GPT5_MINI_TEXT_MODEL,
}

COMPLEX_DOUBT_KEYWORDS = [
    "why",
    "how",
    "prove",
    "derive",
    "explain",
    "step by step",
    "reason",
    "reasoning",
    "diagram",
    "formula",
    "concept",
    "hots",
    "olympiad",
]


def normalize_model_preference(value: str | None) -> str:
    """Return a supported per-student AI model preference."""
    preference = (value or DEFAULT_MODEL_PREFERENCE).strip().lower()

    if preference in SUPPORTED_MODEL_PREFERENCES:
        return preference

    return DEFAULT_MODEL_PREFERENCE


def is_complex_doubt(mode: str, question: str) -> bool:
    """
    Decide whether an Ask Doubt request deserves the premium reasoning model.

    SOF doubts and questions asking for reasoning, proof, diagrams, formulas, or
    step-wise explanation benefit most from GPT-5. Short factual CBSE questions
    stay on the default model unless an admin override is set.
    """
    text = (question or "").strip().lower()

    if (mode or "").strip().upper() == "SOF":
        return True

    if len(text.split()) >= 24:
        return True

    return any(keyword in text for keyword in COMPLEX_DOUBT_KEYWORDS)


def resolve_student_feature_model(
    profile: dict | None,
    feature: str,
    question: str = "",
    mode: str = "",
) -> str:
    """
    Select the LLM model for premium student features.

    Admin-selected `ai_model_preference` wins. If the preference is default,
    Family Premium students use GPT-5 for SOF mock generation and complex Ask
    Doubt requests. Everyone else stays on the existing default model.
    """
    profile = profile or {}
    preference = normalize_model_preference(profile.get("ai_model_preference"))

    if preference != DEFAULT_MODEL_PREFERENCE:
        return preference

    if profile.get("subscription_plan") != "family_premium":
        return DEFAULT_TEXT_MODEL

    if feature == "sof_mock_test":
        return GPT5_TEXT_MODEL

    if feature == "doubt" and is_complex_doubt(mode, question):
        return GPT5_TEXT_MODEL

    return DEFAULT_TEXT_MODEL
