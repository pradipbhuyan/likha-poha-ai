import os
from dotenv import load_dotenv

load_dotenv()


class Settings:

    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    VENICE_API_KEY = os.getenv("VENICE_API_KEY")  # Optional — used when provider=venice
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")           # Optional — used when provider=groq (free tier available)
    CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY")   # Optional — used when provider=cerebras (no daily token cap, free)

    AKSHITA_PASSWORD = os.getenv("AKSHITA_PASSWORD")
    PRADIP_PASSWORD = os.getenv("PRADIP_PASSWORD")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

    FRONTEND_URL = os.getenv(
        "FRONTEND_URL",
        "http://localhost:5173"
    )

    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")

    RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
    RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")
    RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET")

    # ── Cloudflare R2 — lesson audio storage ─────────────────────────────
    R2_ACCOUNT_ID = os.getenv("R2_ACCOUNT_ID")           # Cloudflare Account ID
    R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID")     # R2 API Token Access Key ID
    R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY")  # R2 API Token Secret
    R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME", "lesson-audio")
    R2_PUBLIC_URL = os.getenv("R2_PUBLIC_URL", "")       # e.g. https://pub-xxxx.r2.dev

    # ── Observability ──────────────────────────────────────────────────
    SENTRY_DSN = os.getenv("SENTRY_DSN")                 # unset = Sentry disabled (local/dev default)
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")  # tags Sentry events: development | production

    @staticmethod
    def is_production() -> bool:
        """
        True when running in a deployed environment.

        Security gates must not depend on ENVIRONMENT alone. It defaults to
        "development" when unset, and the production deployment was found to
        be running without it — which silently made every
        `ENVIRONMENT == "production"` guard inert in the one place they were
        meant to apply. RENDER is injected by the hosting platform itself and
        cannot be forgotten in a dashboard, so it is treated as authoritative.

        Local development and CI set neither, so they stay non-production and
        keep the demo login and relaxed startup checks.
        """
        if os.getenv("ENVIRONMENT", "").strip().casefold() == "production":
            return True
        return bool(os.getenv("RENDER"))


settings = Settings()
