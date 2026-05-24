from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    success: bool
    username: str | None = None
    role: str | None = None
    message: str

class LessonRequest(BaseModel):
    grade: str
    mode: str
    subject: str
    chapter: str
    step_title: str
    teacher_persona: str = ""
    username: str = "unknown"


class LessonResponse(BaseModel):
    success: bool
    lesson: str | None = None
    message: str

class TTSRequest(BaseModel):
    text: str
    voice: str = "en-IN-NeerjaNeural"
    rate: str = "+0%"
    pitch: str = "+0Hz"

class MockTestRequest(BaseModel):
    grade: str
    mode: str
    subject: str
    chapter: str | None = None
    mock_type: str
    difficulty: str
    question_count: int
    exam_type: str | None = None


class MockTestQuestion(BaseModel):
    id: int
    section: str
    question: str
    options: dict
    answer: str
    explanation: str
    marks: int


class MockTestResponse(BaseModel):
    success: bool
    questions: list[MockTestQuestion] | None = None
    message: str

class DoubtRequest(BaseModel):
    grade: str
    mode: str
    subject: str
    chapter: str
    question: str
    username: str = "unknown"


class DoubtResponse(BaseModel):
    success: bool
    answer: str | None = None
    message: str

class QuizRequest(BaseModel):
    grade: str
    mode: str
    subject: str
    chapter: str
    difficulty: str
    question_count: int

class QuizQuestion(BaseModel):
    id: int
    question: str
    options: dict
    answer: str
    explanation: str

class QuizResponse(BaseModel):
    success: bool
    questions: list[QuizQuestion] | None = None
    message: str

class RagTextUploadRequest(BaseModel):
    username: str
    grade: str
    subject: str
    chapter: str
    title: str
    text: str

class RagUploadResponse(BaseModel):
    success: bool
    message: str
    document_id: int | None = None
    chunks_created: int = 0

class RagSearchRequest(BaseModel):
    grade: str | None = None
    subject: str | None = None
    chapter: str | None = None
    query: str
    match_count: int = 5

class RagSearchResponse(BaseModel):
    success: bool
    results: list[dict] = []
    message: str

class LessonFollowUpRequest(BaseModel):
    grade: str
    mode: str
    subject: str
    chapter: str
    step_title: str
    lesson: str
    question: str
    username: str = "unknown"


class LessonFollowUpResponse(BaseModel):
    success: bool
    answer: str | None = None
    source_type: str = "LLM"
    sources: list[dict] = []
    message: str