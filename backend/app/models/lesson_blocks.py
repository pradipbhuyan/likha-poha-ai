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

    @field_validator("milestones")
    @classmethod
    def _non_empty(cls, v):
        if not v or all(len(m.blocks) == 0 for m in v):
            raise ValueError("chapter doc must contain at least one non-empty milestone")
        return v
