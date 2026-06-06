from decimal import Decimal, ROUND_HALF_UP


MIN_INCENTIVE_PERCENT = Decimal("5")
MAX_INCENTIVE_PERCENT = Decimal("10")


def normalize_incentive_percent(value) -> Decimal:
    """Return a sales incentive percent clamped to the supported 5-10% range."""
    percent = Decimal(str(value or MIN_INCENTIVE_PERCENT))

    if percent < MIN_INCENTIVE_PERCENT:
        return MIN_INCENTIVE_PERCENT

    if percent > MAX_INCENTIVE_PERCENT:
        return MAX_INCENTIVE_PERCENT

    return percent.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_incentive_amount(package_amount, incentive_percent) -> float:
    """Calculate payable incentive for one student/package sale in INR."""
    amount = Decimal(str(package_amount or 0))
    percent = normalize_incentive_percent(incentive_percent)
    payable = amount * percent / Decimal("100")

    return float(payable.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def enrich_sales_attribution(row: dict) -> dict:
    """Attach a computed incentive amount to a sales attribution row."""
    package_amount = int(row.get("package_amount") or 0)
    incentive_percent = normalize_incentive_percent(
        row.get("incentive_percent"),
    )

    return {
        **row,
        "package_amount": package_amount,
        "incentive_percent": float(incentive_percent),
        "incentive_amount": calculate_incentive_amount(
            package_amount,
            incentive_percent,
        ),
    }
