from decimal import Decimal

import pytest

from app.services.sales_service import (
    build_sales_collateral_storage_path,
    calculate_incentive_amount,
    enrich_sales_attribution,
    infer_collateral_format,
    normalize_sales_collateral_payload,
    normalize_incentive_percent,
    validate_sales_collateral_upload,
)


def test_normalize_incentive_percent_clamps_to_allowed_range():
    assert normalize_incentive_percent(3) == Decimal("5")
    assert normalize_incentive_percent(12) == Decimal("10")
    assert normalize_incentive_percent(7.256) == Decimal("7.26")


def test_calculate_incentive_amount_uses_saved_package_amount():
    assert calculate_incentive_amount(1499, 10) == 149.9
    assert calculate_incentive_amount(499, 5) == 24.95


def test_enrich_sales_attribution_adds_payable_amount():
    row = {
        "package_amount": 999,
        "incentive_percent": 7.5,
    }

    enriched = enrich_sales_attribution(row)

    assert enriched["package_amount"] == 999
    assert enriched["incentive_percent"] == 7.5
    assert enriched["incentive_amount"] == 74.93


def test_normalize_sales_collateral_payload_requires_title():
    with pytest.raises(ValueError, match="Collateral title is required"):
        normalize_sales_collateral_payload({"title": " "})


def test_normalize_sales_collateral_payload_clamps_fields():
    payload = normalize_sales_collateral_payload({
        "title": "  WhatsApp pitch  ",
        "audience": "unknown",
        "channel": "unknown",
        "format": "unknown",
        "status": "unknown",
        "display_order": "4",
        "caption": "Use this for a parent follow-up.",
    })

    assert payload["title"] == "WhatsApp pitch"
    assert payload["audience"] == "parents"
    assert payload["channel"] == "whatsapp"
    assert payload["format"] == "image"
    assert payload["status"] == "active"
    assert payload["display_order"] == 4
    assert payload["caption"] == "Use this for a parent follow-up."


def test_infer_collateral_format_from_content_type_and_filename():
    assert infer_collateral_format("image/png", "poster.png") == "image"
    assert infer_collateral_format("video/mp4", "reel.mp4") == "video"
    assert infer_collateral_format("application/pdf", "brochure") == "pdf"
    assert infer_collateral_format("", "script.md") == "text"
    assert infer_collateral_format("", "landing-page") == "link"


def test_validate_sales_collateral_upload_rejects_bad_files():
    with pytest.raises(ValueError, match="Choose a collateral file"):
        validate_sales_collateral_upload("", "image/png", 10)

    with pytest.raises(ValueError, match="empty"):
        validate_sales_collateral_upload("poster.png", "image/png", 0)

    with pytest.raises(ValueError, match="100 MB"):
        validate_sales_collateral_upload(
            "large.mp4",
            "video/mp4",
            101 * 1024 * 1024,
        )

    with pytest.raises(ValueError, match="Only images"):
        validate_sales_collateral_upload("sheet.xlsx", "application/excel", 20)


def test_build_sales_collateral_storage_path_sanitizes_name_and_channel():
    path = build_sales_collateral_storage_path(
        filename="June Launch Poster!!.png",
        channel="instagram_reel",
        content_type="image/png",
    )

    assert path.startswith("instagram_reel/")
    assert path.endswith("-June-Launch-Poster.png")

    fallback_path = build_sales_collateral_storage_path(
        filename="",
        channel="unknown",
        content_type="application/pdf",
    )

    assert fallback_path.startswith("whatsapp/")
    assert fallback_path.endswith("-collateral.pdf")
