import os
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.services.logger_service import get_logger, PlatformError  # noqa: F401 — PlatformError re-exported
from app.middleware.tracing import TracingMiddleware

_log = get_logger("main")

# Fix macOS SSL certificate verification before any HTTPS connections are made.
# Uses the system trust store (truststore package) which handles local and
# corporate-network certs. Silent no-op when truststore is unavailable.
from app.services.ssl_service import enable_system_truststore as _enable_ssl
_enable_ssl()
_log.info("SSL trust store initialised.")

from app.routes.auth import router as auth_router
from app.routes.syllabus import router as syllabus_router
from app.routes.lesson import router as lesson_router
from app.routes.tts import router as tts_router
from app.routes.mock_test import router as mock_test_router
from app.routes.analytics import router as analytics_router
from app.routes.progress import router as progress_router
from app.routes.doubt import router as doubt_router
from app.routes.quiz import router as quiz_router
from app.routes.resources import router as resources_router
from app.routes.rag import router as rag_router
from app.routes import images
from app.routes import usage
from app.routes import recommendations
from app.routes import profile
from app.routes.evaluation import router as evaluation_router
from app.routes.parent_dashboard import router as parent_dashboard_router
from app.routes.parent_dashboard_v2 import router as parent_dashboard_v2_router
from app.routes.student_dashboard import router as student_dashboard_router
from app.routes.parent_dashboard_p2 import router as parent_dashboard_p2_router
from app.routes.admin_control import router as admin_control_router
from app.routes.offer import router as offer_router
from app.routes.teacher_dashboard import router as teacher_dashboard_router
from app.routes.weak_area_alerts import router as weak_area_alerts_router
from app.routes.payments import router as payments_router
from app.routes.sales import router as sales_router
from app.routes.performance_tests import router as performance_tests_router
from app.routes.onboarding_guide import router as onboarding_guide_router
from app.routes.cache_management import router as cache_management_router
from app.routes.product_catalogue import router as product_catalogue_router
from app.routes.teacher import router as teacher_router
from app.routes.teacher_classroom import router as teacher_classroom_router
from app.routes.teacher_classroom_p2 import router as teacher_classroom_p2_router
from app.routes.subscription import router as subscription_router
from app.routes.admin_operations import router as admin_operations_router
from app.routes.admin_bulk import router as admin_bulk_router
from app.routes.admin_views import router as admin_views_router
from app.routes.admin_analytics import router as admin_analytics_router
from app.routes.admin_support import router as admin_support_router


frontend_url = os.getenv(
    "FRONTEND_URL",
    "http://localhost:5173",
)

allowed_origins = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    "http://localhost:3000",
    "http://127.0.0.1:3000",

    "https://cbse-tutor-platform.vercel.app",

    "https://likhapoha.in",
    "https://www.likhapoha.in",

    frontend_url,
]

app = FastAPI(
    title="CBSE Tutor API",
    version="1.0.0",
)

# ── Middleware stack ──────────────────────────────────────────────────────────
# Starlette applies middleware in REVERSE registration order on responses.
# CORSMiddleware must be registered FIRST so it runs LAST on the response path,
# guaranteeing CORS headers are present even on 4xx/5xx error responses.
# If TracingMiddleware is registered first it wraps CORSMiddleware and
# error responses produced inside route handlers never get CORS headers.
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(set(allowed_origins)),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(TracingMiddleware)

origins = allowed_origins


app.include_router(
    auth_router,
    prefix="/api/auth",
    tags=["Authentication"]
)

app.include_router(
    syllabus_router,
    prefix="/api/syllabus",
    tags=["Syllabus"]
)

app.include_router(
    lesson_router,
    prefix="/api/lesson",
    tags=["Lesson"]
)

app.include_router(
    tts_router,
    prefix="/api/tts",
    tags=["Text To Speech"]
)

app.include_router(
    mock_test_router,
    prefix="/api/mock-test",
    tags=["Mock Test"]
)

app.include_router(
    analytics_router,
    prefix="/api/analytics",
    tags=["Analytics"]
)

app.include_router(
    progress_router,
    prefix="/api/progress",
    tags=["Progress"]
)

app.include_router(
    doubt_router,
    prefix="/api/doubt",
    tags=["Doubt"]
)

app.include_router(
    quiz_router,
    prefix="/api/quiz",
    tags=["Quiz"]
)

app.include_router(
    resources_router,
    prefix="/api/resources",
    tags=["Resources"]
)

app.include_router(
    rag_router,
    prefix="/api/rag",
    tags=["RAG"]
)

app.include_router(
    admin_control_router,
    prefix="/api/admin-control",
    tags=["Admin Control"],
)

app.include_router(
    offer_router,
    prefix="/api/offer",
    tags=["Offer Codes"],
)

app.include_router(images.router, prefix="/api/images", tags=["Images"])
app.include_router(usage.router, prefix="/api/usage", tags=["Usage"])

app.include_router(
    recommendations.router,
    prefix="/api/recommendations",
    tags=["Recommendations"],
)

app.include_router(
    profile.router,
    prefix="/api/profile",
    tags=["Profile"],
)

app.include_router(
    evaluation_router,
    prefix="/api/evaluation",
    tags=["Evaluation"],
)

app.include_router(
    parent_dashboard_router,
    prefix="/api/parent-dashboard",
    tags=["Parent Dashboard"]
)

app.include_router(
    student_dashboard_router,
    prefix="/api/student",
    tags=["Student Dashboard"],
)

app.include_router(
    parent_dashboard_v2_router,
    prefix="/api/parent",
    tags=["Parent Dashboard Phase 1"],
)

app.include_router(
    parent_dashboard_p2_router,
    prefix="/api/parent",
    tags=["Parent Dashboard Phase 2"],
)

app.include_router(
    teacher_dashboard_router,
    prefix="/api/teacher-dashboard",
    tags=["Teacher Dashboard"],
)

app.include_router(
    weak_area_alerts_router,
    prefix="/api/weak-area-alerts",
    tags=["Weak Area Alerts"],
)

app.include_router(
    payments_router,
    prefix="/api/payments",
    tags=["Payments"],
)

app.include_router(
    sales_router,
    prefix="/api/sales",
    tags=["Sales"],
)

app.include_router(
    performance_tests_router,
    prefix="/api/performance-tests",
    tags=["Performance Tests"],
)

app.include_router(
    onboarding_guide_router,
    prefix="/api/onboarding-guide",
    tags=["Onboarding Guide"],
)

app.include_router(
    cache_management_router,
    prefix="/api/cache-management",
    tags=["Cache Management"],
)

app.include_router(
    admin_operations_router,
    prefix="/api/admin/operations",
    tags=["Admin Operations"],
)

app.include_router(
    admin_bulk_router,
    prefix="/api/admin/bulk",
    tags=["Admin Bulk Operations"],
)

app.include_router(
    admin_views_router,
    prefix="/api/admin",
    tags=["Admin Saved Views"],
)

app.include_router(
    admin_analytics_router,
    prefix="/api/admin",
    tags=["Admin Analytics"],
)

app.include_router(
    admin_support_router,
    prefix="/api/admin",
    tags=["Admin Support Tools"],
)

app.include_router(
    product_catalogue_router,
    prefix="/api/product-catalogue",
    tags=["Product Catalogue"],
)

# Public chatbot widget — no auth required
from app.routes.chatbot import router as chatbot_router  # noqa: E402
app.include_router(chatbot_router, prefix="/api/chatbot", tags=["Chatbot"])

# Unanswered questions review (admin intelligence management)
from app.routes.unanswered_review import router as unanswered_router  # noqa: E402
app.include_router(unanswered_router, prefix="/api/unanswered-review", tags=["Unanswered Review"])

app.include_router(
    teacher_classroom_router,
    prefix="/api/teacher",
    tags=["Teacher Classroom"],
)

app.include_router(
    teacher_classroom_p2_router,
    prefix="/api/teacher",
    tags=["Teacher Classroom Phase 2"],
)

app.include_router(
    teacher_router,
    prefix="/api/teacher",
    tags=["Teacher"],
)

app.include_router(
    subscription_router,
    prefix="/api/subscription",
    tags=["Subscription"],
)

@app.get("/api/platform-settings/lesson-card")
def get_lesson_card_settings_public():
    """Return the active lesson card style and theme — public, no auth required."""
    from app.routes.admin_control import _load_lesson_card_settings  # noqa: PLC0415
    return {"success": True, **_load_lesson_card_settings()}


@app.get("/api/health")
def health_check():
    """Return a detailed health response for frontend/API uptime checks."""
    return {
        "status": "ok",
        "message": "Backend is healthy"
    }

@app.get("/")
def health_check():
    """Return a root-level health response for browsers and platform probes."""
    return {
        "status": "ok",
        "message": "CBSE Tutor API is running"
    }

@app.get("/api/health")
def api_health():
    """Return a compact API health response for clients expecting success=true."""
    return {
        "success": True
    }


@app.get("/api/health/dependencies")
def dependency_health():
    """Report optional runtime dependencies used by advanced upload flows."""
    pymupdf = {
        "available": False,
        "version": None,
        "error": None,
    }

    try:
        import fitz

        pymupdf["available"] = True
        pymupdf["version"] = getattr(fitz, "version", None)
    except Exception as exc:
        pymupdf["error"] = f"{type(exc).__name__}: {exc}"

    return {
        "success": True,
        "python_executable": sys.executable,
        "pymupdf": pymupdf,
    }
