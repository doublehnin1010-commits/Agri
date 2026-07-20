# Myanmar Proverbs Local AI Assistant

A local-first RAG assistant built with FastAPI, LangChain, ChromaDB, Ollama, and faster-whisper. No AI API key or paid AI service is required.

## Architecture

```text
Microphone
   |
   v
Browser MediaRecorder
   |
   v
FastAPI /api/v1/speech-to-text
   |
   v
faster-whisper (local STT)
   |
   v
LangChain RAG pipeline
   |-- ChromaDB
   |-- OllamaEmbeddings (bge-m3)
   `-- ChatOllama (qwen3:0.6b)
   |
   v
Generated answer
   |
   v
Edge TTS Myanmar neural voice (optional, internet required)
```

The frontend always records audio and sends it to the local FastAPI endpoint. It does not use the browser's online speech-recognition service. TTS uses Edge TTS through the backend and needs no API key, but it requires internet access and can be muted.

## Required local services and models

1. Install and start MongoDB.
2. Install and start Ollama.
3. Pull the local models:

```powershell
ollama pull qwen3:0.6b
ollama pull bge-m3
```

`nomic-embed-text` can replace `bge-m3`, but changing embedding models requires rebuilding the Chroma collection.

4. Install FFmpeg and ensure `ffmpeg` is on `PATH`, or set `FFMPEG_PATH` to the executable.

## Backend setup

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload
```

Important local model settings:

```env
OLLAMA_BASE_URL="http://localhost:11434"
OLLAMA_MODEL="qwen3:0.6b"
CHAT_MODEL="qwen3:0.6b"
UTILITY_MODEL="qwen3:0.6b"
EMBEDDING_MODEL="bge-m3"
WHISPER_MODEL="base"
WHISPER_DEVICE="auto"
WHISPER_COMPUTE_TYPE="auto"
WHISPER_BEAM_SIZE=5
WHISPER_VAD_SILENCE_MS=500
WHISPER_LOCAL_FILES_ONLY=true
```

The public faster-whisper model is downloaded automatically on first use and then loaded from the local cache. No token or login is configured by this project. For a network-isolated deployment, populate the model cache during installation before disconnecting the machine.

Backend API documentation is available at `http://127.0.0.1:8000/docs`.

## Frontend setup

```powershell
cd frontend
npm install
npm run dev
```

Set `VITE_API_URL=http://127.0.0.1:8000` in `frontend/.env` when needed. Microphone capture requires localhost or a secure HTTPS context.

## Main endpoints

- `POST /api/v1/speech-to-text` - local faster-whisper transcription
- `POST /api/v1/chat` - local RAG answer generation
- `POST /api/v1/import-excel` - import dataset rows
- `POST /api/v1/reindex` - rebuild the Chroma index
- `GET /health` - backend health check

## Local-first boundary

- LLM generation goes only to the configured local Ollama URL.
- Embeddings go only to the configured local Ollama URL.
- Vector data is persisted in local ChromaDB storage.
- Speech transcription runs in the backend with faster-whisper.
- No cloud AI keys or authentication variables are required.
- Optional TTS uses Edge TTS with `my-MM-NilarNeural` by default; it requires internet but no API key.
