import asyncio
import io

from PIL import Image
from starlette.datastructures import UploadFile

from app.routers.chat import _read_validated_image
from app.services import rag


def _png_bytes() -> bytes:
    image = Image.new("RGB", (8, 8), (40, 140, 50))
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def test_image_validation_accepts_supported_image():
    image_bytes, mime_type = asyncio.run(
        _read_validated_image(UploadFile(io.BytesIO(_png_bytes()), filename="leaf.png", headers={"content-type": "image/png"}))
    )

    assert image_bytes.startswith(b"\x89PNG")
    assert mime_type == "image/png"


def test_image_validation_rejects_corrupted_image():
    try:
        asyncio.run(
            _read_validated_image(UploadFile(io.BytesIO(b"not-an-image"), filename="leaf.png", headers={"content-type": "image/png"}))
        )
    except Exception as error:
        assert getattr(error, "status_code", None) == 400
    else:
        raise AssertionError("corrupted image should be rejected")


def test_image_answer_analyzes_then_retrieves_and_answers(monkeypatch):
    calls: list[tuple[str, bytes, str]] = []

    async def fake_multimodal(prompt, image_bytes, mime_type, *, system_instruction=None):
        calls.append((prompt, image_bytes, mime_type))
        if len(calls) == 1:
            return '{"is_agriculture": true, "image_quality": "good", "visible_symptoms": ["yellow spots"], "possible_causes": ["leaf disease"], "search_description": "rice leaf yellow spots"}'
        assert "rice leaf guidance" in prompt
        assert "Image analysis based on visible evidence" in prompt
        return "ပုံအရ အရွက်မှာ အစက်အပြောက်များ တွေ့ရပြီး ရောဂါဖြစ်နိုင်ပါတယ်။"

    async def fake_retrieve(query, top_k=None):
        assert "rice leaf yellow spots" in query
        return [{"filename": "rice-guide.txt", "content": "rice leaf guidance", "document_id": "doc-1", "chunk_id": 1}]

    monkeypatch.setattr(rag, "agenerate_multimodal_response", fake_multimodal)
    monkeypatch.setattr(rag, "aretrieve_context", fake_retrieve)

    answer = asyncio.run(rag.arag_image_answer("ဒီအရွက်မှာ ဘာဖြစ်တာလဲ။", b"image-bytes", "image/png"))

    assert answer["language"] == "my"
    assert answer["sources"][0]["filename"] == "rice-guide.txt"
    assert len(calls) == 2
    assert all(call[1] == b"image-bytes" for call in calls)


def test_image_answer_requests_better_image_when_quality_is_poor(monkeypatch):
    async def fake_multimodal(*args, **kwargs):
        return '{"is_agriculture": true, "image_quality": "poor", "visible_symptoms": [], "possible_causes": [], "search_description": ""}'

    monkeypatch.setattr(rag, "agenerate_multimodal_response", fake_multimodal)

    answer = asyncio.run(rag.arag_image_answer("What is wrong with this leaf?", b"image-bytes", "image/png"))

    assert "not clear enough" in answer["answer"]
    assert answer["sources"] == []


def test_image_answer_rejects_non_agriculture_image(monkeypatch):
    async def fake_multimodal(*args, **kwargs):
        return '{"is_agriculture": false, "image_quality": "good", "visible_symptoms": [], "possible_causes": [], "search_description": ""}'

    monkeypatch.setattr(rag, "agenerate_multimodal_response", fake_multimodal)

    answer = asyncio.run(rag.arag_image_answer("What is this?", b"image-bytes", "image/png"))

    assert "agriculture-related" in answer["answer"]
    assert answer["sources"] == []


def test_image_answer_returns_localized_gemini_failure(monkeypatch):
    async def fake_multimodal(*args, **kwargs):
        raise RuntimeError("Gemini unavailable")

    monkeypatch.setattr(rag, "agenerate_multimodal_response", fake_multimodal)

    answer = asyncio.run(rag.arag_image_answer("ဒီအရွက်မှာ ဘာဖြစ်တာလဲ။", b"image-bytes", "image/png"))

    assert answer["error"] == "gemini_failed"
    assert "Gemini" in answer["answer"]