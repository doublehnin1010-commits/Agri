from fastapi import APIRouter, Depends, File, UploadFile
from starlette.concurrency import run_in_threadpool

from app.core.deps import get_current_user_id
from app.services.speech_service import transcribe_speech

router = APIRouter()


@router.post("/speech-to-text")
async def speech_to_text(
    audio: UploadFile = File(...),
    _user_id: str = Depends(get_current_user_id),
):
    audio_bytes = await audio.read()
    return await run_in_threadpool(transcribe_speech, audio_bytes, audio.filename, audio.content_type)
