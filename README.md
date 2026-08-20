# Agriculture AI Assistant

Full-stack agriculture RAG assistant using FastAPI, MongoDB, ChromaDB, Gemini, and React.

Admins upload agriculture documents (`.pdf`, `.docx`, `.txt`). The backend extracts text, chunks it, embeds chunks with Gemini embeddings, stores vectors in ChromaDB, and saves document metadata in MongoDB. Users ask farming questions in English or Myanmar and receive Gemini answers grounded in retrieved document chunks.

## Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload
```

Required `.env` values:

```env
MONGODB_URI="mongodb://localhost:27017"
JWT_SECRET_KEY="change-this-secret"
GEMINI_API_KEY="your_key"
GEMINI_MODEL="gemini-2.5-flash"
GEMINI_EMBEDDING_MODEL="models/text-embedding-004"
TOP_K=5
CHUNK_SIZE=1000
CHUNK_OVERLAP=150
MAX_UPLOAD_MB=50
```

## Frontend

```powershell
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

## Main APIs

- `POST /api/v1/register`
- `POST /api/v1/login`
- `POST /api/v1/chat`
- `GET /api/v1/history`
- `POST /api/v1/documents/upload`
- `GET /api/v1/documents`
- `GET /api/v1/documents/{document_id}`
- `DELETE /api/v1/documents/{document_id}`
- `POST /api/v1/documents/{document_id}/process`

Admin document APIs require an admin user. Gemini keys stay on the backend and are never exposed to the frontend.
