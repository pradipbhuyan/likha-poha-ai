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


settings = Settings()
