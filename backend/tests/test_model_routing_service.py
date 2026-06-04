from app.services.model_routing_service import resolve_student_feature_model
from app.services.openai_service import (
    DEFAULT_TEXT_MODEL,
    GPT5_MINI_TEXT_MODEL,
    GPT5_TEXT_MODEL,
)


def test_default_student_uses_existing_model_for_premium_features():
    """Default plan/default preference should stay on the existing model."""
    profile = {
        "subscription_plan": "starter",
        "ai_model_preference": "default",
    }

    assert (
        resolve_student_feature_model(profile, "sof_mock_test")
        == DEFAULT_TEXT_MODEL
    )


def test_family_premium_uses_gpt5_for_sof_mock_tests():
    """Family Premium should automatically upgrade SOF mock generation."""
    profile = {
        "subscription_plan": "family_premium",
        "ai_model_preference": "default",
    }

    assert (
        resolve_student_feature_model(profile, "sof_mock_test")
        == GPT5_TEXT_MODEL
    )


def test_family_premium_uses_gpt5_for_complex_doubts_only():
    """Simple CBSE doubts remain cheaper; reasoning-heavy doubts use GPT-5."""
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
        == GPT5_TEXT_MODEL
    )


def test_admin_model_preference_wins_over_plan_defaults():
    """Admin-selected GPT-5 mini should override automatic plan routing."""
    profile = {
        "subscription_plan": "family_premium",
        "ai_model_preference": "gpt-5-mini",
    }

    assert (
        resolve_student_feature_model(profile, "sof_mock_test")
        == GPT5_MINI_TEXT_MODEL
    )
