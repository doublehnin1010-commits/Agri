# Burmese Proverbs Hub

Burmese Proverbs Hub is a full-stack RAG application for learning, searching, explaining, quizzing, and saving Myanmar traditional proverbs. It combines a FastAPI backend, ChromaDB vector search, MongoDB user data, Ollama local models, and a React + TypeScript frontend.

## Features

- User authentication with JWT
- Admin dataset management
- DOCX dataset import and ChromaDB indexing
- RAG chat for Myanmar proverb questions
- Dataset-only proverb answers with source grounding
- English and Myanmar explanation support
- Voice input with backend speech-to-text
- Optional text-to-speech playback
- Chat history stored in MongoDB
- AI Quiz Mode from the indexed proverb dataset
- Favorite Proverbs with per-user MongoDB storage
- Favorites page with detail modal
- Responsive React + Tailwind UI

## Tech Stack

Backend:

- FastAPI
- MongoDB with Motor
- ChromaDB
- LangChain
- Ollama
- Gemini for speech-to-text and optional chat fallback
- Edge TTS

Frontend:

- React
- TypeScript
- Vite
- Tailwind CSS
- React Query
- Zustand
- Axios
- Lucide icons

## Project Structure

```text
D:\RAG
|-- backend
|   |-- app
|   |   |-- core
|   |   |-- db
|   |   |-- models
|   |   |-- routers
|   |   |-- services
|   |   `-- main.py
|   |-- chroma_data
|   |-- requirements.txt
|   `-- .env.example
|-- frontend
|   |-- src
|   |   |-- api
|   |   |-- components
|   |   |-- contexts
|   |   |-- hooks
|   |   |-- layouts
|   |   |-- pages
|   |   |-- routes
|   |   |-- services
|   |   `-- types
|   `-- package.json
`-- README.md
```

## Prerequisites

Install these before running the project:

- Python 3.11+
- Node.js 20+
- MongoDB
- Ollama
- FFmpeg

Pull the local Ollama models:

```powershell
ollama pull qwen3:0.6b
ollama pull bge-m3
```

`bge-m3` is used for embeddings. If you change the embedding model, rebuild the ChromaDB index.

## Backend Setup

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `backend/.env`:

```env
MONGODB_URI="mongodb://localhost:27017"
MONGODB_DB_NAME="mm_proverbs_ai"
JWT_SECRET_KEY="change-this-secret"

OLLAMA_BASE_URL="http://localhost:11434"
CHAT_PROVIDER="ollama"
CHAT_MODEL="qwen3:0.6b"
UTILITY_MODEL="qwen3:0.6b"
EMBEDDING_MODEL="bge-m3"

GEMINI_API_KEY=""
FFMPEG_PATH="ffmpeg"
ADMIN_EMAIL="admin@example.com"
```

Start the backend:

```powershell
uvicorn app.main:app --reload
```

Backend docs:

```text
http://127.0.0.1:8000/docs
```

Health check:

```text
GET http://127.0.0.1:8000/health
```

## Frontend Setup

```powershell
cd frontend
npm install
npm run dev
```

The frontend runs at:

```text
https://127.0.0.1:5173
```

If needed, create `frontend/.env`:

```env
VITE_API_URL=http://127.0.0.1:8000
```

The API client automatically appends `/api/v1`.

## Authentication

Users can register and log in from the frontend.

Main auth APIs:

```text
POST /api/v1/register
POST /api/v1/login
```

JWT tokens are sent with:

```text
Authorization: Bearer <token>
```

Admin-only routes are protected by role-based middleware.

## Dataset and RAG

The proverb dataset is stored in ChromaDB with metadata such as:

- proverb
- meaning
- english_meaning
- keyword
- category
- example

The RAG pipeline uses:

- semantic retrieval from ChromaDB
- lexical fallback search
- metadata awareness
- query rewrite support when enabled
- dataset-only guardrails

The assistant should not invent new proverbs. Proverbs and meanings must come from the indexed dataset.

## Main Backend APIs

Chat:

```text
POST /api/v1/chat
```

History:

```text
GET /api/v1/history
PATCH /api/v1/history/{conversation_id}
DELETE /api/v1/history/{conversation_id}
```

Proverbs:

```text
GET /api/v1/proverbs
POST /api/v1/proverbs
PUT /api/v1/proverbs/{proverb_id}
DELETE /api/v1/proverbs/{proverb_id}
DELETE /api/v1/proverbs
```

Import and reindex:

```text
POST /api/v1/import-docx
GET /api/v1/import-docx/status/{job_id}
POST /api/v1/reindex
```

Voice:

```text
POST /api/v1/speech-to-text
POST /api/v1/transcribe
POST /api/v1/speech
```

Quiz:

```text
POST /api/v1/quiz/start
POST /api/v1/quiz/submit
```

Favorites:

```text
POST /api/v1/favorites/{proverb_id}
DELETE /api/v1/favorites/{proverb_id}
GET /api/v1/favorites
GET /api/v1/favorites/check/{proverb_id}
```

## AI Quiz Mode

Quiz Mode lets users practice meanings from the dataset.

Frontend route:

```text
/quiz
```

Start quiz request:

```json
{
  "difficulty": "easy",
  "question_count": 5
}
```

Quiz questions are generated quickly from the indexed dataset. The system uses dataset meanings as correct answers and other dataset meanings as distractors.

Submit quiz request:

```json
{
  "quiz_id": "...",
  "answers": [
    {
      "question_id": 1,
      "selected": 2
    }
  ]
}
```

The result screen shows:

- final score
- percentage
- correct answers
- wrong answers
- review cards

## Favorite Proverbs

Users can save proverbs to their personal favorites.

Frontend route:

```text
/favorites
```

Favorites are stored in MongoDB as references only:

- user_id
- proverb_id
- created_at

The app does not duplicate proverb data. The favorites page hydrates proverb details from the existing ChromaDB collection.

Favorite features:

- Favorite button on proverb answer cards
- Favorite button on related proverb cards
- Favorites page
- Empty state with `Explore Proverbs`
- Detail modal for each favorite
- Remove favorite button

## Voice Features

The frontend records audio through the browser and sends it to the backend.

Backend flow:

```text
Browser MediaRecorder
  -> FastAPI upload endpoint
  -> FFmpeg preprocessing
  -> Gemini speech-to-text
  -> RAG chat
  -> optional Edge TTS
```

FFmpeg must be installed and available on `PATH`, or configured with:

```env
FFMPEG_PATH="C:\\ffmpeg\\bin\\ffmpeg.exe"
```

## Frontend Pages

User pages:

```text
/dashboard   Main chat and proverb assistant
/history     Chat history
/quiz        Quiz mode
/favorites   Saved favorite proverbs
```

Auth pages:

```text
/login
/register
```

Admin pages:

```text
/admin
/admin/import
/admin/proverbs
```

## Development Commands

Backend compile check:

```powershell
python -m compileall backend/app
```

Frontend build:

```powershell
cd frontend
npm run build
```

Frontend dev server:

```powershell
cd frontend
npm run dev -- --host 127.0.0.1 --port 5173
```

## Notes

- MongoDB must be running before backend startup.
- Ollama must be running before using chat, embeddings, or reindex features.
- Gemini API key is required for Gemini speech-to-text.
- Edge TTS requires internet access.
- If ChromaDB embedding dimensions mismatch, rebuild the dataset index.
- New favorite buttons require proverb ids in answer payloads, so older saved chat messages may not show favorite controls.

## License

This project is for educational use and Myanmar proverb preservation.
