from app.data.platform_info import (
    LIKHA_POHA_FOUNDER_STORY,
    LIKHA_POHA_FOUNDER_STORY_TITLE,
    LIKHA_POHA_PLATFORM_CHAPTER,
    LIKHA_POHA_PLATFORM_GRADE,
    LIKHA_POHA_PLATFORM_SUBJECT,
)
from app.services.rag_service import upload_textbook_text


def main():
    """
    Seed the approved Likha Poha AI founder story into Supabase RAG tables.

    Run from the backend directory with real Supabase/OpenAI environment
    variables configured:
        python -m scripts.seed_platform_founder_story
    """
    result = upload_textbook_text(
        username="admin",
        grade=LIKHA_POHA_PLATFORM_GRADE,
        subject=LIKHA_POHA_PLATFORM_SUBJECT,
        chapter=LIKHA_POHA_PLATFORM_CHAPTER,
        title=LIKHA_POHA_FOUNDER_STORY_TITLE,
        text=LIKHA_POHA_FOUNDER_STORY,
    )

    print(result)


if __name__ == "__main__":
    main()
