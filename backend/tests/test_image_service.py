from app.services.image_service import validate_visual_context


def test_visual_context_allows_science_and_maths():
    """Science and Maths are the only subjects where generated visuals are useful enough."""
    assert validate_visual_context(subject="Science", mode="CBSE")["allowed"]
    assert validate_visual_context(subject="Maths", mode="CBSE")["allowed"]


def test_visual_context_blocks_language_subjects():
    """Language subjects should not spend image-generation cost on low-value visuals."""
    result = validate_visual_context(subject="English", mode="CBSE")

    assert result["allowed"] is False
    assert "Science and Maths" in result["message"]
