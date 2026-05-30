from fastapi import APIRouter

from app.models.schemas import (
    MockTestRequest,
    MockTestResponse,
)

from app.services.mock_test_service import (
    generate_olympiad_mock_test,
    generate_cbse_mock_test,
)

router = APIRouter()


@router.post("/generate", response_model=MockTestResponse)
def generate_mock_test(data: MockTestRequest):

    try:

        if data.mock_type == "SOF Olympiad Mock Test":

            questions = generate_olympiad_mock_test(
                olympiad=data.subject,
                chapter=data.chapter,
                grade=data.grade,
                num_questions=data.question_count,
                difficulty=data.difficulty,
            )
            
        else:

            questions = generate_cbse_mock_test(
                subject=data.subject,
                chapter=data.chapter,
                exam_type=data.exam_type or "Class Test",
                num_questions=data.question_count,
                difficulty=data.difficulty,
            )

        return MockTestResponse(
            success=True,
            questions=questions,
            message="Mock test generated successfully",
        )

    except Exception as e:

        return MockTestResponse(
            success=False,
            questions=[],
            message=str(e),
        )