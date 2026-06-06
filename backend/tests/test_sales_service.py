from decimal import Decimal

from app.services.sales_service import (
    calculate_incentive_amount,
    enrich_sales_attribution,
    normalize_incentive_percent,
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
