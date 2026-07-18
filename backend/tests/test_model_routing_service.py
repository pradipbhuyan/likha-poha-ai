from app.services.model_routing_service import resolve_student_feature_model
from app.services.openai_service import (
    DEFAULT_TEXT_MODEL,
    GPT_MINI_TEXT_MODEL,
    GPT_FULL_TEXT_MODEL,
)


def test_default_student_uses_existing_model_for_premium_features():
    """Default plan/default preference should stay on gpt-4.1-nano (cheapest)."""
    profile = {
        "subscription_plan": "starter",
        "ai_model_preference": "default",
    }

    assert (
        resolve_student_feature_model(profile, "teacher_tool")
        == DEFAULT_TEXT_MODEL
    )


def test_family_premium_auto_upgrades_complex_doubts_only():
    """Simple CBSE doubts stay on nano; reasoning-heavy doubts get gpt-4.1-mini."""
    profile = {
        "subscription_plan": "family_premium",
        "ai_model_preference": "default",
    }

    assert (
        resolve_student_feature_model(
            profile,
            "doubt",
            question="What is matter?",
            mode="CBSE",
        )
        == DEFAULT_TEXT_MODEL
    )
    assert (
        resolve_student_feature_model(
            profile,
            "doubt",
            question="Explain step by step why osmosis happens in cells.",
            mode="CBSE",
        )
        == GPT_MINI_TEXT_MODEL
    )


def test_admin_model_preference_mini_wins_over_plan_defaults():
    """Admin-pinned gpt-4.1-mini should override automatic plan routing."""
    profile = {
        "subscription_plan": "family_premium",
        "ai_model_preference": "gpt-4.1-mini",
    }

    assert (
        resolve_student_feature_model(profile, "teacher_tool")
        == GPT_MINI_TEXT_MODEL
    )


def test_admin_model_preference_full_wins_over_plan_defaults():
    """Admin-pinned gpt-4.1 (full) should override automatic plan routing."""
    profile = {
        "subscription_plan": "starter",
        "ai_model_preference": "gpt-4.1",
    }

    assert (
        resolve_student_feature_model(profile, "teacher_tool")
        == GPT_FULL_TEXT_MODEL
    )


def test_unknown_preference_falls_back_to_default():
    """An unrecognised preference (e.g. old 'gpt-5-mini') falls back to default routing."""
    profile = {
        "subscription_plan": "starter",
        "ai_model_preference": "gpt-5-mini",  # legacy / unknown value
    }

    assert (
        resolve_student_feature_model(profile, "teacher_tool")
        == DEFAULT_TEXT_MODEL
    )
