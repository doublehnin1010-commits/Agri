# 🌱 Agriculture AI Assistant

A full-stack, bilingual **Retrieval-Augmented Generation (RAG)** assistant that answers farming questions using a curated library of agriculture documents — not open-ended guesses.

Admins upload agriculture documents (`.pdf`, `.docx`, `.txt`). The backend extracts the text, splits it into chunks, embeds each chunk with Gemini embeddings, and stores the vectors in ChromaDB while metadata lives in MongoDB. Farmers ask questions in **English or Myanmar** and receive Gemini-generated answers grounded in the retrieved document chunks.

---

## ✨ Features

- 📄 **Document ingestion** — upload PDF, DOCX, and TXT agriculture references
- ✂️ **Automatic chunking** — configurable chunk size and overlap
- 🧠 **Gemini embeddings** — semantic vector representation of every chunk
- 🔍 **Retrieval-augmented answers** — responses are grounded in the top-K most relevant chunks, reducing hallucination
- 🌐 **Bilingual Q&A** — ask and receive answers in English or Myanmar
- 🔐 **Role-based access** — document management is restricted to authenticated admins
- 🗂️ **Full document lifecycle** — upload, list, view, process, and delete documents
- 💬 **Chat history** — past conversations are saved per user

---

## 🏗️ Architecture

```
┌────────────┐     upload      ┌─────────────┐   extract & chunk   ┌───────────────┐
│   Admin    │ ───────────────▶│   FastAPI   │────────────────────▶│ Gemini Embed  │
└────────────┘                 │   Backend   │                     └───────┬───────┘
                                │             │                             │
┌────────────┐     ask (EN/MY) │             │      store vectors          ▼
│   Farmer   │ ───────────────▶│             │◀────────────────────┌───────────────┐
└────────────┘   grounded ans. │             │      metadata        │   ChromaDB    │
                 ◀──────────── │             │─────────────────────▶│  MongoDB     │
                                └─────────────┘                     └───────────────┘
```

**Frontend (React)** — chat interface for farmers, admin dashboard for document management
**Backend (FastAPI)** — REST APIs for auth, chat, history, and document management
**MongoDB** — document metadata and user data
**ChromaDB** — vector store for chunk embeddings
**Gemini** — embeddings + grounded answer generation

---

## 🧰 Tech Stack

| Layer      | Technology                          |
|------------|--------------------------------------|
| Frontend   | React                                |
| Backend    | FastAPI (Python)                     |
| Database   | MongoDB (metadata), ChromaDB (vectors) |
| AI / LLM   | Google Gemini (chat + embeddings)    |
| Auth       | JWT                                  |

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+
- A running MongoDB instance
- A Google Gemini API key

### Backend Setup

```bash
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1      # Windows
# source .venv/bin/activate       # macOS/Linux

pip install -r requirements.txt
Copy-Item .env.example .env       # or: cp .env.example .env
uvicorn app.main:app --reload
```

Configure `.env` with the values below, then start the server.

### Frontend Setup

```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

---

## ⚙️ Environment Variables

Set these in `backend/.env`:

| Variable                  | Description                                  |
|----------------------------|-----------------------------------------------|
| `MONGODB_URI`              | MongoDB connection string                     |
| `JWT_SECRET_KEY`           | Secret used to sign JWTs                      |
| `GEMINI_API_KEY`           | Your Google Gemini API key                    |
| `GEMINI_MODEL`             | Chat model, e.g. `gemini-2.5-flash`           |
| `GEMINI_EMBEDDING_MODEL`   | Embedding model, e.g. `models/text-embedding-004` |
| `TOP_K`                    | Number of chunks retrieved per query          |
| `CHUNK_SIZE`                | Character length per chunk                    |
| `CHUNK_OVERLAP`             | Overlap between consecutive chunks            |
| `MAX_UPLOAD_MB`             | Maximum upload size in megabytes              |

> Gemini keys stay on the backend and are never exposed to the frontend.

---

## 📡 Main API Endpoints

| Method | Endpoint                                        | Description                        |
|--------|--------------------------------------------------|-------------------------------------|
| POST   | `/api/v1/register`                               | Create a new user account           |
| POST   | `/api/v1/login`                                  | Authenticate and receive a JWT      |
| POST   | `/api/v1/chat`                                   | Ask a farming question              |
| GET    | `/api/v1/history`                                | Retrieve past conversation history  |
| POST   | `/api/v1/documents/upload`                       | Upload a new agriculture document (admin) |
| GET    | `/api/v1/documents`                              | List all documents (admin)          |
| GET    | `/api/v1/documents/{document_id}`                | Get a single document's details     |
| POST   | `/api/v1/documents/{document_id}/process`        | Chunk, embed, and index a document  |
| DELETE | `/api/v1/documents/{document_id}`                | Remove a document                   |

---

## 📁 Project Structure

```
Agriculture/
├── backend/     # FastAPI app, RAG pipeline, auth, APIs
├── frontend/    # React chat + admin interface
├── public/      # Static assets
└── render.yaml  # Deployment configuration
```

---

## 🗺️ Roadmap Ideas

- [ ] Add support for additional document types (images, spreadsheets)
- [ ] Expand language support beyond English and Myanmar
- [ ] Add answer citations linking back to source documents
- [ ] Usage analytics dashboard for admins

---
