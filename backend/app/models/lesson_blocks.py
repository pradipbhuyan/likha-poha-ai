"""
Chapter Journey block schema
============================
Typed, validated lesson content — the contract between prewarm-time
generation/conversion and the two student renderers (Journey 5-8, Study 9-12).

Every chapter is ONE document: an ordered list of milestones, each holding
typed blocks. Renderers switch on `type`; they never parse markdown headings.

Validation happens server-side BEFORE a document is stored, so students only
ever receive documents that passed. See chapter_doc_service.py for the
lesson_cache → ChapterDoc converter.
"""

from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field, field_validator


class KeyTerm(BaseModel):
    term: str
    meaning: str


class HookBlock(BaseModel):
    """Curiosity opener — Journey renderer only; Study renderer skips it."""
    type: Literal["hook"] = "hook"
    text: str


class ConceptBlock(BaseModel):
    type: Literal["concept"] = "concept"
    title: str = ""
    body_md: str
    key_terms: list[KeyTerm] = []


class ExampleBlock(BaseModel):
    """Worked example: self-contained question plus stepped solution."""
    type: Literal["example"] = "example"
    question: str
    body_md: str  # the stepped solution (markdown, may embed visual-json)


class QuickCheckBlock(BaseModel):
    """MCQ / True-False check. Evaluated locally — never an LLM call."""
    type: Literal["quickcheck"] = "quickcheck"
    format: Literal["mcq", "truefalse"] = "mcq"
    question: str
    options: list[str]
    answer_index: int
    explanation: str = ""

    @field_validator("options")
    @classmethod
    def _at_least_two_options(cls, v):
        if len(v) < 2:
            raise ValueError("quickcheck needs at least 2 options")
        return v

    @field_validator("answer_index")
    @classmethod
    def _answer_in_range(cls, v, info):
        options = info.data.get("options") or []
        if options and not (0 <= v < len(options)):
            raise ValueError("answer_index out of range")
        return v


class WatchoutBlock(BaseModel):
    """Common mistake / misconception warning."""
    type: Literal["watchout"] = "watchout"
    body_md: str


class VocabBlock(BaseModel):
    """New words extracted from the textbook passage (language subjects)."""
    type: Literal["vocab"] = "vocab"
    words: list[KeyTerm]


class StudentsAskBlock(BaseModel):
    """Pre-warmed LKB Q&A attached to a milestone (zero LLM at serving)."""
    type: Literal["students_ask"] = "students_ask"
    question: str
    answer_md: str


class RecapBlock(BaseModel):
    """Exactly one per chapter — the single summary/revision block."""
    type: Literal["recap"] = "recap"
    body_md: str


_VISUAL_TYPES = {"flow", "steps", "cycle", "compare"}


class VisualBlock(BaseModel):
    """Validated structured visual (flow/steps/cycle/compare).
    Extracted from visual-json fences at conversion time — raw JSON must
    NEVER reach a renderer as text."""
    type: Literal["visual"] = "visual"
    visual: dict

    @field_validator("visual")
    @classmethod
    def _valid_visual(cls, v):
        vtype = v.get("type")
        if vtype not in _VISUAL_TYPES:
            raise ValueError(f"visual.type must be one of {_VISUAL_TYPES}")
        if vtype == "compare":
            columns, rows = v.get("columns"), v.get("rows")
            if not (isinstance(columns, list) and len(columns) == 2):
                raise ValueError("compare visual needs exactly 2 columns")
            if not (isinstance(rows, list) and 1 <= len(rows) <= 6):
                raise ValueError("compare visual needs 1-6 rows")
        else:
            items = v.get("items")
            if not (isinstance(items, list) and 2 <= len(items) <= 6
                    and all(isinstance(i, str) and i.strip() for i in items)):
                raise ValueError("visual needs 2-6 non-empty string items")
        return v


class ExamQABlock(BaseModel):
    """Board-style question with model answer — Grades 9-12 Study mode only.
    Rendered after the recap as a "Board questions" section; the model answer
    is gated behind an attempt-first reveal."""
    type: Literal["exam_qa"] = "exam_qa"
    marks: int = 3
    year: str = ""          # e.g. "CBSE 2023" when sourced from a PYQ; "" for generated
    question: str
    model_answer_md: str

    @field_validator("marks")
    @classmethod
    def _marks_range(cls, v):
        if not (1 <= v <= 10):
            raise ValueError("marks must be between 1 and 10")
        return v


Block = Annotated[
    Union[
        HookBlock,
        ConceptBlock,
        ExampleBlock,
        QuickCheckBlock,
        WatchoutBlock,
        VocabBlock,
        StudentsAskBlock,
        RecapBlock,
        VisualBlock,
    ],
    Field(discriminator="type"),
]


class Milestone(BaseModel):
    title: str
    blocks: list[Block]


class ChapterDoc(BaseModel):
    board: str
    grade: str
    subject: str
    chapter: str
    mode: str = "CBSE"
    version: int = 1
    # "converted" = built from existing lesson_cache markdown (Phase 1)
    # "prewarm_v2" = generated natively as structured output (Phase 3)
    source: Literal["converted", "prewarm_v2"] = "converted"
    milestones: list[Milestone]
    recap: RecapBlock | None = None
    # Board-style questions (Grades 9-12) — rendered as a final section by the
    # Study renderer; Journey (5-8) ignores this list.
    exam: list[ExamQABlock] = []

    @field_validator("milestones")
    @classmethod
    def _non_empty(cls, v):
        if not v or all(len(m.blocks) == 0 for m in v):
            raise ValueError("chapter doc must contain at least one non-empty milestone")
        return v
