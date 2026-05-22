from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
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

frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")

app = FastAPI(
    title="CBSE Tutor API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        frontend_url,
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

origins = [
    settings.FRONTEND_URL,
]


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

@app.get("/")
def health_check():
    return {
        "status": "ok",
        "message": "CBSE Tutor API is running"
    }

@app.get("/api/health")
def api_health():
    return {
        "success": True
    }
