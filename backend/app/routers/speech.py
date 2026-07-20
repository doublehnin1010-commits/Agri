from fastapi import APIRouter, Depends, File, Form, Response, UploadFile
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from app.core.deps import get_current_user_id
from app.services.speech_service import transcribe_speech
from app.services.tts_service import synthesize_speech

router = APIRouter()


class TextToSpeechRequest(BaseModel):
    text: str
    language: str = "my-MM"


@router.post("/speech-to-text")
async def speech_to_text(
    audio: UploadFile = File(...),
    language: str = Form("my"),
    _user_id: str = Depends(get_current_user_id),
):
    audio_bytes = await audio.read()
    return await run_in_threadpool(
        transcribe_speech,
        audio_bytes,
        audio.filename,
        audio.content_type,
        language,
    )


@router.post("/text-to-speech")
async def text_to_speech(
    payload: TextToSpeechRequest,
    _user_id: str = Depends(get_current_user_id),
):
    audio = await synthesize_speech(payload.text, payload.language)
    return Response(
        content=audio,
        media_type="audio/mpeg",
        headers={"Cache-Control": "no-store"},
    )
