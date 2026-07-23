import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.deps import get_current_user
from app.models.quiz import QuizStartRequest, QuizStartResponse, QuizSubmitRequest, QuizSubmitResponse
from app.services.quiz_service import start_quiz, submit_quiz


logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/quiz/start", response_model=QuizStartResponse)
async def start_quiz_route(payload: QuizStartRequest, user=Depends(get_current_user)):
    try:
        return await start_quiz(payload, user.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception:
        logger.exception("Failed to start quiz.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to start quiz.")


@router.post("/quiz/submit", response_model=QuizSubmitResponse)
async def submit_quiz_route(payload: QuizSubmitRequest, user=Depends(get_current_user)):
    try:
        return await submit_quiz(payload, user.id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except Exception:
        logger.exception("Failed to submit quiz.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to submit quiz.")
