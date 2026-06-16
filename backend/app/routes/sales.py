import os

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app.services.auth_service import (
    admin_client,
    create_auth_user,
    require_admin,
    require_admin_or_sales,
)
from app.services.sales_service import (
    build_sales_collateral_storage_path,
    calculate_incentive_amount,
    enrich_sales_attribution,
    infer_collateral_format,
    normalize_sales_collateral_payload,
    normalize_incentive_percent,
    validate_sales_collateral_upload,
)


router = APIRouter()
SALES_COLLATERAL_BUCKET = os.getenv(
    "SALES_COLLATERAL_BUCKET",
    "sales-collaterals",
)


class CreateSalesPersonRequest(BaseModel):
    email: str
    password: str
    username: str
    salesperson_type: str = "independent"
    region: str = ""
    phone: str = ""
    status: str = "active"
    default_incentive_percent: float = Field(default=5, ge=5, le=10)


class LeadClaimRequest(BaseModel):
    """Sales person self-submits a student lead — no admin needed."""
    student_email: str
    student_name: str
    student_phone: str = ""
    grade: str = "Grade 9"
    package_key: str = "starter"


class BatchPayRequest(BaseModel):
    """Admin marks a list of confirmed claims as commission-paid."""
    claim_ids: list[str]  # UUIDs of confirmed claims to mark paid


# ---------------------------------------------------------------------------
# Lead-claims helpers
# ---------------------------------------------------------------------------

CLAIM_EXPIRY_DAYS = 30
DAILY_CLAIM_LIMIT = 15


def _expire_stale_claims() -> None:
    """Lazily mark claims older than CLAIM_EXPIRY_DAYS as expired."""
    from datetime import datetime, timedelta, timezone
    cutoff = (datetime.now(timezone.utc) - timedelta(days=CLAIM_EXPIRY_DAYS)).isoformat()
    try:
        admin_client.table("sales_lead_claims").update({"status": "expired"}).eq(
            "status", "claimed"
        ).lt("claimed_at", cutoff).execute()
    except Exception:
        pass  # table may not exist yet


def _get_salesperson_incentive_percent(sales_person_id: str) -> float:
    """Look up the salesperson's default incentive percent from their profile."""
    try:
        r = (
            admin_client.table("sales_profiles")
            .select("default_incentive_percent")
            .eq("profile_id", sales_person_id)
            .limit(1)
            .execute()
        )
        if r.data:
            return float(r.data[0].get("default_incentive_percent") or 5)
    except Exception:
        pass
    return 5.0


def auto_match_lead_claim(email: str, student_id: str, package_amount: int, package_key: str) -> None:
    """
    Called from complete_signup after a student pays.

    Looks up an active (non-expired) lead claim for the student's email
    and auto-confirms it with commission calculated.
    """
    from datetime import datetime, timezone
    from decimal import Decimal, ROUND_HALF_UP

    try:
        r = (
            admin_client.table("sales_lead_claims")
            .select("*")
            .eq("student_email", email.strip().lower())
            .eq("status", "claimed")
            .limit(1)
            .execute()
        )
        if not r.data:
            return  # no claim — nothing to do

        claim = r.data[0]
        incentive_pct = Decimal(str(claim.get("incentive_percent") or 5))
        commission = float(
            (Decimal(str(package_amount)) * incentive_pct / Decimal("100"))
            .quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        )

        admin_client.table("sales_lead_claims").update({
            "status": "confirmed",
            "student_id": student_id,
            "package_amount": package_amount,
            "package_key": package_key or claim.get("package_key") or "starter",
            "commission_amount": commission,
            "confirmed_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", claim["id"]).execute()

    except Exception:
        pass  # never block signup due to sales tracking error


class CreateSalesAttributionRequest(BaseModel):
    sales_profile_id: str
    student_id: str
    package_key: str = "free"
    package_label: str = "Free Trial"
    package_amount: int = Field(default=0, ge=0)
    incentive_percent: float = Field(default=5, ge=5, le=10)
    status: str = "pending"
    notes: str = ""


class UpdateSalesAttributionRequest(BaseModel):
    package_key: str | None = None
    package_label: str | None = None
    package_amount: int | None = Field(default=None, ge=0)
    incentive_percent: float | None = Field(default=None, ge=5, le=10)
    status: str | None = None
    notes: str | None = None


class SalesCollateralRequest(BaseModel):
    title: str
    audience: str = "parents"
    channel: str = "whatsapp"
    format: str = "image"
    description: str = ""
    caption: str = ""
    asset_url: str = ""
    thumbnail_url: str = ""
    status: str = "active"
    display_order: int = 999


def _safe_table_rows(table_name: str, select_value: str = "*") -> list[dict]:
    """Read optional sales tables without breaking the page before SQL is run."""
    try:
        response = admin_client.table(table_name).select(select_value).execute()
        return response.data or []
    except Exception:
        return []


def _profiles_by_role(role: str) -> list[dict]:
    """Return profiles for one app role."""
    response = (
        admin_client
        .table("profiles")
        .select("*")
        .eq("role", role)
        .order("created_at", desc=True)
        .execute()
    )

    return response.data or []


def _profiles_by_id(rows: list[dict]) -> dict[str, dict]:
    """Index profile rows by id for enrichment."""
    return {
        row.get("id"): row
        for row in rows
        if row.get("id")
    }


def _collateral_rows_for_role(role: str) -> list[dict]:
    """Return collateral rows, hiding drafts from non-admin sales users."""
    try:
        query = (
            admin_client
            .table("sales_collaterals")
            .select("*")
            .order("display_order")
            .order("created_at", desc=True)
        )
        if role != "admin":
            query = query.eq("status", "active")
        response = query.execute()
        return response.data or []
    except Exception:
        return []


def build_sales_summary(profile: dict) -> dict:
    """Build admin or salesperson sales dashboard data from Supabase rows."""
    role = profile.get("role")
    is_sales = role == "sales"
    current_profile_id = profile.get("id")

    sales_profiles = _safe_table_rows("sales_profiles")
    sales_metadata_by_id = {
        item.get("profile_id"): item
        for item in sales_profiles
        if item.get("profile_id")
    }

    sales_people = _profiles_by_role("sales")
    students = _profiles_by_role("student")
    attributions = _safe_table_rows("sales_student_attributions")

    if is_sales:
        sales_people = [
            person for person in sales_people
            if person.get("id") == current_profile_id
        ]
        attributions = [
            row for row in attributions
            if row.get("sales_profile_id") == current_profile_id
        ]

    sales_by_id = _profiles_by_id(sales_people)
    students_by_id = _profiles_by_id(students)

    enriched_sales_people = []
    for person in sales_people:
        metadata = sales_metadata_by_id.get(person.get("id"), {})
        enriched_sales_people.append({
            **person,
            "sales_profile": metadata,
        })

    enriched_attributions = []
    for row in attributions:
        enriched = enrich_sales_attribution(row)
        sales_profile = sales_by_id.get(row.get("sales_profile_id"), {})
        student_profile = students_by_id.get(row.get("student_id"), {})
        enriched_attributions.append({
            **enriched,
            "salesperson": sales_profile,
            "student": student_profile,
        })

    total_revenue = sum(
        int(row.get("package_amount") or 0)
        for row in enriched_attributions
        if row.get("status") != "cancelled"
    )
    incentive_payable = sum(
        float(row.get("incentive_amount") or 0)
        for row in enriched_attributions
        if row.get("status") in {"active", "paid", "pending"}
    )

    return {
        "success": True,
        "role": role,
        "sales_people": enriched_sales_people,
        "students": students,
        "attributions": enriched_attributions,
        "summary": {
            "sales_people": len(enriched_sales_people),
            "tracked_students": len(enriched_attributions),
            "total_revenue": total_revenue,
            "incentive_payable": round(incentive_payable, 2),
        },
    }


@router.get("/summary")
def get_sales_summary(user=Depends(require_admin_or_sales)):
    """Return sales incentive data for admins or the signed-in salesperson."""
    return build_sales_summary(user["profile"])


@router.get("/collaterals")
def get_sales_collaterals(user=Depends(require_admin_or_sales)):
    """Return the sales collateral library for admins and sales users."""
    return {
        "success": True,
        "collaterals": _collateral_rows_for_role(user["profile"].get("role")),
    }


@router.post("/collaterals/upload")
async def upload_sales_collateral_file(
    file: UploadFile = File(...),
    channel: str = Form(default="whatsapp"),
    admin=Depends(require_admin),
):
    """Upload a collateral file to Supabase Storage and return its public URL."""
    file_bytes = await file.read()
    content_type = file.content_type or "application/octet-stream"

    try:
        validate_sales_collateral_upload(
            filename=file.filename or "",
            content_type=content_type,
            size_bytes=len(file_bytes),
        )
        storage_path = build_sales_collateral_storage_path(
            filename=file.filename or "collateral",
            channel=channel,
            content_type=content_type,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    try:
        admin_client.storage.from_(SALES_COLLATERAL_BUCKET).upload(
            path=storage_path,
            file=file_bytes,
            file_options={
                "content-type": content_type,
                "upsert": "false",
            },
        )
        public_url = admin_client.storage.from_(
            SALES_COLLATERAL_BUCKET,
        ).get_public_url(storage_path)
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unable to upload collateral to Supabase Storage bucket "
                f"'{SALES_COLLATERAL_BUCKET}'. Create this bucket and make it "
                f"public, then try again. Original error: {str(exc)}"
            ),
        )

    return {
        "success": True,
        "bucket": SALES_COLLATERAL_BUCKET,
        "path": storage_path,
        "asset_url": public_url,
        "format": infer_collateral_format(content_type, file.filename or ""),
        "content_type": content_type,
        "size_bytes": len(file_bytes),
    }


@router.post("/collaterals")
def create_sales_collateral(
    data: SalesCollateralRequest,
    admin=Depends(require_admin),
):
    """Create a sales collateral entry that salespeople can download or copy."""
    try:
        row = normalize_sales_collateral_payload(data.model_dump())
        row["uploaded_by"] = admin["profile"].get("id")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    try:
        response = admin_client.table("sales_collaterals").insert(row).execute()
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=(
                "Unable to save sales collateral. Make sure "
                "backend/sql/add_sales_collaterals.sql has been executed in "
                f"Supabase. Original error: {str(exc)}"
            ),
        )

    return {
        "success": True,
        "collateral": response.data[0] if response.data else row,
    }


@router.patch("/collaterals/{collateral_id}")
def update_sales_collateral(
    collateral_id: str,
    data: SalesCollateralRequest,
    admin=Depends(require_admin),
):
    """Update a sales collateral entry from the admin page."""
    try:
        update_data = normalize_sales_collateral_payload(data.model_dump())
        update_data["uploaded_by"] = admin["profile"].get("id")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    response = (
        admin_client
        .table("sales_collaterals")
        .update(update_data)
        .eq("id", collateral_id)
        .execute()
    )

    if not response.data:
        raise HTTPException(status_code=404, detail="Sales collateral not found.")

    return {
        "success": True,
        "collateral": response.data[0],
    }


@router.delete("/collaterals/{collateral_id}")
def delete_sales_collateral(
    collateral_id: str,
    admin=Depends(require_admin),
):
    """Delete a sales collateral entry from the admin page."""
    response = (
        admin_client
        .table("sales_collaterals")
        .delete()
        .eq("id", collateral_id)
        .execute()
    )

    if response.data is None:
        raise HTTPException(status_code=404, detail="Sales collateral not found.")

    return {
        "success": True,
        "deleted_id": collateral_id,
    }


@router.post("/people")
def create_sales_person(
    data: CreateSalesPersonRequest,
    admin=Depends(require_admin),
):
    """Create a sales login/profile from the admin panel only."""
    salesperson_type = data.salesperson_type
    if salesperson_type not in {"school", "independent", "partner"}:
        salesperson_type = "independent"

    auth_user = create_auth_user(
        email=data.email,
        password=data.password,
    )

    profile = {
        "id": auth_user.id,
        "email": data.email,
        "username": data.username,
        "role": "sales",
        "parent_id": None,
        "family_id": None,
        "account_status": data.status or "active",
        "subscription_plan": "sales",
        "access_cbse": False,
        "access_sof_science": False,
        "access_sof_maths": False,
        "access_sof_english": False,
    }
    metadata = {
        "profile_id": auth_user.id,
        "salesperson_type": salesperson_type,
        "region": data.region or "",
        "phone": data.phone or "",
        "status": data.status or "active",
        "default_incentive_percent": float(
            normalize_incentive_percent(data.default_incentive_percent),
        ),
    }

    try:
        profile_response = admin_client.table("profiles").insert(profile).execute()
        metadata_response = (
            admin_client.table("sales_profiles").insert(metadata).execute()
        )
    except Exception as exc:
        try:
            admin_client.table("profiles").delete().eq("id", auth_user.id).execute()
            admin_client.auth.admin.delete_user(auth_user.id)
        except Exception:
            pass

        raise HTTPException(
            status_code=400,
            detail=(
                "Unable to create sales profile. Make sure "
                "backend/sql/add_sales_incentive.sql has been executed in "
                f"Supabase. Original error: {str(exc)}"
            ),
        )

    saved_profile = profile_response.data[0] if profile_response.data else profile
    saved_profile["sales_profile"] = (
        metadata_response.data[0] if metadata_response.data else metadata
    )

    return {
        "success": True,
        "salesperson": saved_profile,
    }


@router.post("/attributions")
def create_sales_attribution(
    data: CreateSalesAttributionRequest,
    admin=Depends(require_admin),
):
    """Track which salesperson onboarded a student and for which package."""
    row = {
        "sales_profile_id": data.sales_profile_id,
        "student_id": data.student_id,
        "package_key": data.package_key or "free",
        "package_label": data.package_label or data.package_key or "Free Trial",
        "package_amount": int(data.package_amount or 0),
        "incentive_percent": float(normalize_incentive_percent(data.incentive_percent)),
        "status": data.status or "pending",
        "notes": data.notes or "",
    }

    try:
        response = (
            admin_client
            .table("sales_student_attributions")
            .upsert(row, on_conflict="student_id")
            .execute()
        )
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=(
                "Unable to save sales attribution. Make sure "
                "backend/sql/add_sales_incentive.sql has been executed in "
                f"Supabase. Original error: {str(exc)}"
            ),
        )

    saved_row = response.data[0] if response.data else row

    return {
        "success": True,
        "attribution": enrich_sales_attribution(saved_row),
    }


@router.patch("/attributions/{attribution_id}")
def update_sales_attribution(
    attribution_id: str,
    data: UpdateSalesAttributionRequest,
    admin=Depends(require_admin),
):
    """Update package, status, notes, or incentive percent for one sale."""
    update_data = {}

    for field in ["package_key", "package_label", "package_amount", "status", "notes"]:
        value = getattr(data, field)
        if value is not None:
            update_data[field] = value

    if data.incentive_percent is not None:
        update_data["incentive_percent"] = float(
            normalize_incentive_percent(data.incentive_percent),
        )

    if not update_data:
        raise HTTPException(status_code=400, detail="No attribution updates supplied.")

    response = (
        admin_client
        .table("sales_student_attributions")
        .update(update_data)
        .eq("id", attribution_id)
        .execute()
    )

    if not response.data:
        raise HTTPException(status_code=404, detail="Sales attribution not found.")

    return {
        "success": True,
        "attribution": enrich_sales_attribution(response.data[0]),
        "incentive_amount": calculate_incentive_amount(
            response.data[0].get("package_amount"),
            response.data[0].get("incentive_percent"),
        ),
    }


# ---------------------------------------------------------------------------
# Lead-claim endpoints (self-service for sales persons)
# ---------------------------------------------------------------------------

@router.post("/lead-claims")
def submit_lead_claim(data: LeadClaimRequest, user=Depends(require_admin_or_sales)):
    """
    Sales person self-submits a student lead.

    Anti-malpractice checks (all automated):
    - First-claim-wins: UNIQUE(student_email) blocks duplicate claims
    - Cannot claim already-paid students
    - Cannot exceed DAILY_CLAIM_LIMIT per day
    """
    from datetime import datetime, timedelta, timezone

    sales_person_id = user["profile"]["id"]
    email_clean = (data.student_email or "").strip().lower()

    if not email_clean or "@" not in email_clean:
        raise HTTPException(status_code=400, detail="Valid student email is required.")
    if not data.student_name.strip():
        raise HTTPException(status_code=400, detail="Student name is required.")

    # Anti-malpractice: cannot claim a student who already has a paid plan
    existing_profile = (
        admin_client.table("profiles")
        .select("id, subscription_plan, account_status")
        .eq("email", email_clean)
        .limit(1)
        .execute()
    )
    if existing_profile.data:
        profile = existing_profile.data[0]
        if profile.get("subscription_plan") not in ("free", None, ""):
            raise HTTPException(
                status_code=409,
                detail="This student already has an active paid account.",
            )

    # Anti-malpractice: daily claim limit
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    daily_count = (
        admin_client.table("sales_lead_claims")
        .select("id", count="exact")
        .eq("sales_person_id", sales_person_id)
        .gte("claimed_at", today_start)
        .execute()
    )
    if (daily_count.count or 0) >= DAILY_CLAIM_LIMIT:
        raise HTTPException(
            status_code=429,
            detail=f"Daily claim limit of {DAILY_CLAIM_LIMIT} reached. Try again tomorrow.",
        )

    # Get salesperson's incentive percent
    incentive_pct = _get_salesperson_incentive_percent(sales_person_id)

    row = {
        "sales_person_id": sales_person_id,
        "student_email": email_clean,
        "student_name": data.student_name.strip(),
        "student_phone": (data.student_phone or "").strip(),
        "grade": data.grade or "Grade 9",
        "package_key": data.package_key or "starter",
        "status": "claimed",
        "incentive_percent": incentive_pct,
    }

    try:
        result = admin_client.table("sales_lead_claims").insert(row).execute()
    except Exception as exc:
        err_str = str(exc)
        if "unique" in err_str.lower() or "duplicate" in err_str.lower():
            raise HTTPException(
                status_code=409,
                detail="Another sales person has already claimed this student.",
            )
        raise HTTPException(
            status_code=400,
            detail=(
                "Unable to save lead claim. Make sure "
                "backend/sql/add_sales_lead_claims.sql has been run in Supabase. "
                f"Error: {err_str}"
            ),
        )

    return {
        "success": True,
        "claim": result.data[0] if result.data else row,
        "message": f"Lead claimed for {data.student_name}. You will be notified when they complete payment.",
    }


@router.get("/lead-claims")
def get_lead_claims(user=Depends(require_admin_or_sales)):
    """
    Return lead claims.
    - Sales person: their own claims only
    - Admin: all claims with salesperson details
    """
    _expire_stale_claims()

    role = user["profile"].get("role")
    sales_person_id = user["profile"]["id"]

    query = admin_client.table("sales_lead_claims").select("*").order("claimed_at", desc=True)
    if role != "admin":
        query = query.eq("sales_person_id", sales_person_id)

    result = query.execute()
    claims = result.data or []

    # Enrich with salesperson username for admin view
    if role == "admin" and claims:
        sp_ids = list({c["sales_person_id"] for c in claims})
        sp_profiles = (
            admin_client.table("profiles")
            .select("id, username, email")
            .in_("id", sp_ids)
            .execute()
        ).data or []
        sp_by_id = {p["id"]: p for p in sp_profiles}
        for c in claims:
            c["salesperson"] = sp_by_id.get(c["sales_person_id"], {})

    # Summary stats for sales person
    if role != "admin":
        total_commission = sum(
            float(c.get("commission_amount") or 0)
            for c in claims if c.get("status") in ("confirmed", "paid")
        )
        paid_commission = sum(
            float(c.get("commission_amount") or 0)
            for c in claims if c.get("status") == "paid"
        )
        return {
            "success": True,
            "claims": claims,
            "summary": {
                "total": len(claims),
                "confirmed": sum(1 for c in claims if c["status"] == "confirmed"),
                "claimed": sum(1 for c in claims if c["status"] == "claimed"),
                "paid": sum(1 for c in claims if c["status"] == "paid"),
                "expired": sum(1 for c in claims if c["status"] == "expired"),
                "total_commission_earned": round(total_commission, 2),
                "total_commission_paid": round(paid_commission, 2),
                "commission_pending": round(total_commission - paid_commission, 2),
            },
        }

    return {"success": True, "claims": claims}


@router.patch("/lead-claims/batch-pay")
def batch_pay_commissions(data: BatchPayRequest, admin=Depends(require_admin)):
    """
    Admin marks a list of confirmed claims as commission-paid.
    This is the only admin action needed in the normal flow.
    """
    from datetime import datetime, timezone

    if not data.claim_ids:
        raise HTTPException(status_code=400, detail="No claim IDs provided.")

    now = datetime.now(timezone.utc).isoformat()
    result = (
        admin_client.table("sales_lead_claims")
        .update({"status": "paid", "paid_at": now})
        .in_("id", data.claim_ids)
        .eq("status", "confirmed")  # only confirmed → paid; no accidental re-paying
        .execute()
    )

    updated = result.data or []
    return {
        "success": True,
        "paid_count": len(updated),
        "message": f"{len(updated)} commission(s) marked as paid.",
    }


@router.patch("/lead-claims/{claim_id}/manual-confirm")
def manual_confirm_claim(
    claim_id: str,
    payload: dict,
    admin=Depends(require_admin),
):
    """
    Admin manually confirms a lead claim when payment was collected offline
    (e.g. cash, bank transfer, UPI outside Razorpay).

    Admin provides:
    - package_amount: amount actually collected (INR)
    - package_key: which plan (optional, defaults to existing)
    - admin_notes: payment method, reference number, etc.

    Commission is recalculated from the confirmed package amount.
    """
    from datetime import datetime, timezone
    from decimal import Decimal, ROUND_HALF_UP

    # Load the claim
    result = (
        admin_client.table("sales_lead_claims")
        .select("*")
        .eq("id", claim_id)
        .limit(1)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Lead claim not found.")

    claim = result.data[0]

    if claim["status"] == "paid":
        raise HTTPException(status_code=400, detail="This claim has already been paid. Cannot re-confirm.")

    package_amount = int(payload.get("package_amount") or claim.get("package_amount") or 0)
    if package_amount <= 0:
        raise HTTPException(status_code=400, detail="Package amount must be greater than 0 for manual confirmation.")

    incentive_pct = Decimal(str(claim.get("incentive_percent") or 5))
    commission = float(
        (Decimal(str(package_amount)) * incentive_pct / Decimal("100"))
        .quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    )

    update_data = {
        "status": "confirmed",
        "package_amount": package_amount,
        "package_key": payload.get("package_key") or claim.get("package_key") or "starter",
        "commission_amount": commission,
        "confirmed_at": datetime.now(timezone.utc).isoformat(),
        "admin_notes": (payload.get("admin_notes") or "") + " [Manual confirmation by admin]",
    }

    updated = (
        admin_client.table("sales_lead_claims")
        .update(update_data)
        .eq("id", claim_id)
        .execute()
    )

    return {
        "success": True,
        "claim": updated.data[0] if updated.data else {**claim, **update_data},
        "message": f"Claim manually confirmed. Commission = ₹{commission}",
    }


@router.get("/lead-claims/admin-summary")
def get_admin_commission_summary(admin=Depends(require_admin)):
    """
    Monthly commission summary per salesperson for the admin payout view.
    Returns per-person totals of confirmed (unpaid) commission.
    """
    _expire_stale_claims()

    claims = (
        admin_client.table("sales_lead_claims")
        .select("*")
        .in_("status", ["confirmed", "paid"])
        .order("confirmed_at", desc=True)
        .execute()
    ).data or []

    # Get all salesperson profiles
    sp_ids = list({c["sales_person_id"] for c in claims})
    sp_profiles = {}
    if sp_ids:
        sp_data = (
            admin_client.table("profiles")
            .select("id, username, email")
            .in_("id", sp_ids)
            .execute()
        ).data or []
        sp_profiles = {p["id"]: p for p in sp_data}

    # Aggregate by salesperson
    summary_by_sp: dict = {}
    for c in claims:
        sp_id = c["sales_person_id"]
        sp = summary_by_sp.setdefault(sp_id, {
            "sales_person_id": sp_id,
            "username": sp_profiles.get(sp_id, {}).get("username", "Unknown"),
            "email": sp_profiles.get(sp_id, {}).get("email", ""),
            "confirmed_count": 0,
            "confirmed_amount": 0.0,
            "paid_count": 0,
            "paid_amount": 0.0,
            "confirmed_claim_ids": [],
        })
        amt = float(c.get("commission_amount") or 0)
        if c["status"] == "confirmed":
            sp["confirmed_count"] += 1
            sp["confirmed_amount"] = round(sp["confirmed_amount"] + amt, 2)
            sp["confirmed_claim_ids"].append(c["id"])
        elif c["status"] == "paid":
            sp["paid_count"] += 1
            sp["paid_amount"] = round(sp["paid_amount"] + amt, 2)

    return {
        "success": True,
        "salespeople": list(summary_by_sp.values()),
        "total_confirmed_payable": round(
            sum(sp["confirmed_amount"] for sp in summary_by_sp.values()), 2
        ),
    }
