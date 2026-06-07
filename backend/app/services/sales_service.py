import re
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from uuid import uuid4


MIN_INCENTIVE_PERCENT = Decimal("5")
MAX_INCENTIVE_PERCENT = Decimal("10")
SUPPORTED_COLLATERAL_AUDIENCES = {
    "parents",
    "students",
    "teachers",
    "schools",
}
SUPPORTED_COLLATERAL_CHANNELS = {
    "whatsapp",
    "instagram_reel",
    "brochure",
    "demo_script",
    "poster",
}
SUPPORTED_COLLATERAL_FORMATS = {
    "image",
    "video",
    "pdf",
    "text",
    "link",
}
SUPPORTED_COLLATERAL_STATUSES = {
    "active",
    "draft",
    "archived",
}
SALES_COLLATERAL_MAX_BYTES = 100 * 1024 * 1024
SUPPORTED_COLLATERAL_CONTENT_TYPES = {
    "application/pdf",
    "image/gif",
    "image/jpeg",
    "image/png",
    "image/webp",
    "text/plain",
    "video/mp4",
    "video/quicktime",
    "video/webm",
}


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


def normalize_sales_collateral_payload(payload: dict) -> dict:
    """Return a bounded collateral row that is safe to store and show to sales users."""
    title = str(payload.get("title") or "").strip()
    if not title:
        raise ValueError("Collateral title is required.")

    audience = str(payload.get("audience") or "parents").strip().lower()
    channel = str(payload.get("channel") or "whatsapp").strip().lower()
    format_value = str(payload.get("format") or "image").strip().lower()
    status = str(payload.get("status") or "active").strip().lower()

    if audience not in SUPPORTED_COLLATERAL_AUDIENCES:
        audience = "parents"
    if channel not in SUPPORTED_COLLATERAL_CHANNELS:
        channel = "whatsapp"
    if format_value not in SUPPORTED_COLLATERAL_FORMATS:
        format_value = "image"
    if status not in SUPPORTED_COLLATERAL_STATUSES:
        status = "active"

    return {
        "title": title[:160],
        "audience": audience,
        "channel": channel,
        "format": format_value,
        "description": str(payload.get("description") or "").strip()[:600],
        "caption": str(payload.get("caption") or "").strip()[:4000],
        "asset_url": str(payload.get("asset_url") or "").strip()[:1000],
        "thumbnail_url": str(payload.get("thumbnail_url") or "").strip()[:1000],
        "status": status,
        "display_order": int(payload.get("display_order") or 999),
    }


def infer_collateral_format(content_type: str, filename: str = "") -> str:
    """Infer the collateral format shown in the sales library."""
    normalized_type = (content_type or "").lower()
    extension = Path(filename or "").suffix.lower()

    if normalized_type.startswith("image/"):
        return "image"
    if normalized_type.startswith("video/"):
        return "video"
    if normalized_type == "application/pdf" or extension == ".pdf":
        return "pdf"
    if normalized_type.startswith("text/") or extension in {".txt", ".md"}:
        return "text"

    return "link"


def build_sales_collateral_storage_path(
    filename: str,
    channel: str = "whatsapp",
    content_type: str = "",
) -> str:
    """Create a safe Supabase Storage object path for a collateral file."""
    normalized_channel = str(channel or "whatsapp").strip().lower()
    if normalized_channel not in SUPPORTED_COLLATERAL_CHANNELS:
        normalized_channel = "whatsapp"

    original_name = Path(filename or "collateral").name
    safe_stem = re.sub(r"[^a-zA-Z0-9._-]+", "-", Path(original_name).stem)
    safe_stem = safe_stem.strip("-_.")[:80] or "collateral"
    extension = Path(original_name).suffix.lower()

    if not extension:
        inferred_format = infer_collateral_format(content_type, filename)
        extension = {
            "image": ".png",
            "video": ".mp4",
            "pdf": ".pdf",
            "text": ".txt",
        }.get(inferred_format, ".bin")

    date_folder = datetime.now(timezone.utc).strftime("%Y/%m/%d")
    return f"{normalized_channel}/{date_folder}/{uuid4().hex}-{safe_stem}{extension}"


def validate_sales_collateral_upload(
    filename: str,
    content_type: str,
    size_bytes: int,
) -> None:
    """Reject unsupported or oversized collateral uploads before storage."""
    if not filename:
        raise ValueError("Choose a collateral file to upload.")

    if size_bytes <= 0:
        raise ValueError("The uploaded file is empty.")

    if size_bytes > SALES_COLLATERAL_MAX_BYTES:
        raise ValueError("Collateral files must be 100 MB or smaller.")

    normalized_type = (content_type or "").lower()
    if normalized_type and normalized_type not in SUPPORTED_COLLATERAL_CONTENT_TYPES:
        raise ValueError(
            "Only images, MP4/WebM/MOV videos, PDFs, and text files are supported.",
        )
