import os
from dotenv import load_dotenv

load_dotenv()


class Settings:

    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

    AKSHITA_PASSWORD = os.getenv("AKSHITA_PASSWORD")
    PRADIP_PASSWORD = os.getenv("PRADIP_PASSWORD")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

    FRONTEND_URL = os.getenv(
        "FRONTEND_URL",
        "http://localhost:5173"
    )

    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")


settings = Settings()