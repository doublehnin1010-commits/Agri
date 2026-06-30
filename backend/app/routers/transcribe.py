from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.core.deps import get_current_user_id
from app.services.transcription import transcribe_audio_bytes

router = APIRouter()


@router.post("/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...),
    language: str = Form("my-MM"),
    _user_id: str = Depends(get_current_user_id),
):
    audio_bytes = await file.read()
    transcript = transcribe_audio_bytes(audio_bytes, file.filename or "recording.webm", language)
    return {"transcript": transcript}
