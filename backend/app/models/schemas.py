from pydantic import BaseModel, Field


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
    board: str = "CBSE"
    subject: str
    chapter: str
    step_title: str
    teacher_persona: str = ""
    username: str = "unknown"
    # When True the cache is skipped and the lesson is regenerated fresh.
    # Used by the "Refresh lesson" button to replace stale prewarmed content.
    force_refresh: bool = False


class LessonResponse(BaseModel):
    success: bool
    lesson: str | None = None
    source_type: str = "LLM"
    sources: list[dict] = Field(default_factory=list)
    textbook_visuals: list[dict] = Field(default_factory=list)
    message: str

class TTSRequest(BaseModel):
    text: str
    voice: str = "en-IN-NeerjaNeural"
    rate: str = "+0%"
    pitch: str = "+0Hz"

class MockTestRequest(BaseModel):
    grade: str
    mode: str
    board: str = "CBSE"
    subject: str
    chapter: str | None = None
    # Multiple chapters to sample from in one paper (Mid Term / Annual Exam).
    # When non-empty, this takes priority over the single `chapter` field.
    chapters: list[str] = []
    mock_type: str
    difficulty: str
    question_count: int = 10
    exam_type: str | None = None
    # IDs of questions already shown in recent tests — excluded from sampling
    # so the same question doesn't appear in the same or next 30 tests.
    excluded_ids: list[str] = []
    # Question format: "mcq" (default), "written", or "mixed"
    question_format: str = "mcq"

    @classmethod
    def __get_validators__(cls):
        yield cls._validate

    @classmethod
    def _validate(cls, v):
        return v

    def model_post_init(self, __context) -> None:
        # Clamp question_count to 1–100 and duration guard is in frontend
        if self.question_count < 1:
            object.__setattr__(self, 'question_count', 1)
        if self.question_count > 100:
            object.__setattr__(self, 'question_count', 100)


class MockTestQuestion(BaseModel):
    id: int
    section: str
    question: str
    options: dict = Field(default_factory=dict)   # empty for written questions
    answer: str = ""                               # empty for written questions
    explanation: str = ""
    marks: int = 1
    db_id: str | None = None
    question_type: str = "mcq"                    # "mcq" | "written_short" | "written_long"
    model_answer: str | None = None               # reference answer for written questions
    expected_keywords: list[str] = Field(default_factory=list)


class MockTestResponse(BaseModel):
    success: bool
    questions: list[MockTestQuestion] | None = None
    message: str

class DoubtRequest(BaseModel):
    grade: str
    mode: str
    board: str = "CBSE"
    subject: str
    chapter: str
    question: str
    username: str = "unknown"
    display_question: str | None = None
    dkb_id: str | None = None          # suggestion chip ID — enables direct DKB lookup by PK
    save_to_history: bool = True


class DoubtResponse(BaseModel):
    success: bool
    answer: str | None = None
    message: str

class QuizRequest(BaseModel):
    grade: str
    mode: str
    board: str = "CBSE"
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
    board: str = "CBSE"
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
    board: str | None = None
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
    board: str = "CBSE"
    subject: str
    chapter: str
    step_title: str
    lesson: str
    question: str
    username: str = "unknown"


class LessonFollowUpResponse(BaseModel):
    success: bool
    answer: str | None = None
    source_type: str = ""
    sources: list[dict] = []
    textbook_visuals: list[dict] = Field(default_factory=list)
    history_id: str | None = None
    message: str
    

class AnswerEvaluationRequest(BaseModel):
    username: str
    grade: str = "Grade 9"
    mode: str = "CBSE"
    subject: str = ""
    chapter: str = ""
    step_title: str = ""
    question: str
    student_answer: str
    ideal_context: str
    question_type: str = "descriptive"
    expected_keywords: list[str] = Field(default_factory=list)
    correct_answer: str = ""
