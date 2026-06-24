# Myanmar Proverbs AI Tutor for Kids (MVP)

Production-ready MVP: **FastAPI + JWT + MongoDB + ChromaDB + Gemini (RAG)** with optional React (Vite) frontend.

## Folder structure

```
RAG/
  backend/
    app/
      core/
        config.py
        security.py
      db/
        mongodb.py
        chroma.py
      models/
        user.py
        chat.py
      routers/
        auth.py
        chat.py
        import_excel.py
        history.py
      services/
        gemini.py
        rag.py
      main.py
    requirements.txt
    .env.example
  frontend/               # optional
    index.html
    package.json
    vite.config.js
    src/
      main.jsx
      api.js
      App.jsx
      pages/
        Login.jsx
        Chat.jsx
      styles.css
  render.yaml             # optional (Render blueprint)
```

## What this app does (RAG in simple words)

When a user asks a question like “ငါးနဲ့ပတ်သက်တဲ့ စကားပုံ”:

1. We **embed** the user query into a vector (numbers).
2. We **search ChromaDB** to find the most similar proverb rows from the Excel dataset.
3. We send those retrieved proverbs as **context** to **Gemini**.
4. Gemini generates:
   - the relevant proverb(s)
   - meaning in **simple Burmese**
   - an example sentence
5. We return the answer and also store the conversation in **MongoDB**.

## Excel dataset format (example)

Your `.xlsx` must contain these columns exactly:

| keyword | proverb | meaning | example |
|---|---|---|---|
| ငါး | ငါးကြီးက ငါးသေးကို စား | အင်အားကြီးသူက အင်အားနည်းသူကို ဖိအားပေးတတ် | အလုပ်မှာ အကြီးက အငယ်ကို ဖိအားပေးတာ ငါးကြီးက ငါးသေးကို စား လိုပါပဲ |

## Environment variables

Copy `backend/.env.example` to `backend/.env` for local dev.

## Run locally (backend)

```bash
python -m venv .venv
source .venv/Scripts/activate   # Windows Git Bash
pip install -r requirements.txt

uvicorn app.main:app --reload
```

Open docs: `http://127.0.0.1:8000/docs`

## Run locally (frontend - optional)

```bash
cd frontend
npm install
npm run dev
```

Set `VITE_API_BASE_URL` in `frontend/.env` (example: `http://127.0.0.1:8000`).

## API overview

- `POST /register`
- `POST /login`
- `POST /import-excel` (JWT required)
- `POST /chat` (JWT required)
- `GET /history` (JWT required)

## API examples

### Register

**Request**

```json
{
  "email": "kidparent@example.com",
  "password": "StrongPass123",
  "name": "Parent"
}
```

**Response**

```json
{
  "id": "665f...ab",
  "email": "kidparent@example.com",
  "name": "Parent"
}
```

### Login

**Request**

```json
{
  "email": "kidparent@example.com",
  "password": "StrongPass123"
}
```

**Response**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### Import Excel (upload)

`POST /import-excel` with `multipart/form-data`

- form field: `file` = your `.xlsx`
- header: `Authorization: Bearer <token>`

**Response**

```json
{
  "inserted": 1200,
  "skipped": 0,
  "collection": "proverbs"
}
```

### Chat (RAG)

**Request**

```json
{
  "message": "ငါးနဲ့ပတ်သက်တဲ့ စကားပုံ"
}
```

**Response**

```json
{
  "answer": {
    "proverb": "....",
    "meaning_simple_mm": "....",
    "example_mm": "....",
    "sources": [
      {
        "keyword": "ငါး",
        "proverb": "....",
        "meaning": "....",
        "example": "....",
        "score": 0.12
      }
    ]
  }
}
```

## Deployment (Render + MongoDB Atlas)

### 1) MongoDB Atlas setup

- Create a free cluster in MongoDB Atlas.
- Create a database user (username/password).
- Add IP allowlist:
  - For MVP: allow `0.0.0.0/0` (later restrict).
- Copy your connection string, e.g.:
  - `mongodb+srv://USER:PASS@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority`

### 2) Get a Gemini API key

- In Google AI Studio, create an API key.
- Keep it for `GEMINI_API_KEY`.

### 3) Push to GitHub

```bash
git init
git add .
git commit -m "MVP: Myanmar Proverbs AI Tutor (RAG)"
git branch -M main
git remote add origin <your-repo>
git push -u origin main
```

### 4) Deploy on Render (recommended)

Option A (Blueprint):
- In Render, click **New +** → **Blueprint**
- Connect your GitHub repo
- Render will read `render.yaml`

Option B (Manual Web Service):
- Create a **Web Service**
- Root directory: `backend`
- Build command:
  - `pip install -r requirements.txt`
- Start command:
  - `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### 5) Set environment variables on Render

Set these (same as `.env.example`):

- `MONGODB_URI`
- `MONGODB_DB_NAME`
- `JWT_SECRET_KEY`
- `JWT_EXPIRES_MINUTES`
- `GEMINI_API_KEY`
- `GEMINI_MODEL`
- `GEMINI_EMBED_MODEL`
- `CHROMA_PERSIST_DIR`
- `CHROMA_COLLECTION_NAME`
- `RAG_TOP_K`

### 6) Production health check

After deploy, open:
- `https://<your-render-service>/docs`

## Notes

- ChromaDB persistence is local to the Render instance. For an MVP this is OK; for production scaling you’d move vectors to a managed vector DB or use Render persistent disk.

