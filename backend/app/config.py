import os
from dotenv import load_dotenv

load_dotenv()


class Settings:

    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    VENICE_API_KEY = os.getenv("VENICE_API_KEY")  # Optional — used when provider=venice
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")      # Optional — used when provider=groq (free tier available)

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


settings = Settings()
