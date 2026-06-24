# Myanmar Proverbs AI Tutor

A FastAPI backend for answering Myanmar proverb questions with Retrieval Augmented Generation (RAG).

The system searches a local ChromaDB proverb dataset, answers only from that dataset, and explains meanings in friendly Myanmar language like a teacher talking to children.

## Features

- Myanmar proverb Q&A from a ChromaDB dataset
- Two-file Word import: one `.docx` for proverbs and one `.docx` for meanings
- JWT authentication with user roles
- Admin-only dataset and proverb management
- MongoDB chat history storage
- Ollama/Qwen model support for natural answer generation
- Myanmar-aware matching for common issues:
  - tone mark differences
  - small spelling differences
  - joined words
  - selected synonym groups
- Guardrail behavior:
  - relevant proverb exists: answer it
  - relevant proverb missing: return not found
  - unrelated question: return not found
  - role/system question: explain what the tutor does

## Tech Stack

- FastAPI
- MongoDB
- ChromaDB
- Ollama
- Pydantic
- python-docx
- JWT authentication

## Project Structure

```text
RAG/
  backend/
    app/
      core/
        config.py
        deps.py
        roles.py
        security.py
      db/
        chroma.py
        mongodb.py
      middleware/
        rbac.py
      models/
        chat.py
        proverb.py
        user.py
      routers/
        auth.py
        chat.py
        history.py
        import_excel.py
        proverbs.py
        reindex.py
      services/
        guardrails.py
        ollama.py
        rag.py
        reindex.py
      main.py
    requirements.txt
    .env.example
    GUARDRAILS.md
    SEMANTIC_SEARCH_GUIDE.md
    test_guardrails.py
    test_semantic_search.py
  render.yaml
```

Note: `backend/app/routers/import_excel.py` is kept as the existing module name, but the active import endpoint is Word-only: `POST /api/v1/import-docx`.

## How It Works

1. The admin uploads two Word files:
   - `proverbs_file`: one proverb per paragraph
   - `meanings_file`: one meaning per paragraph
2. The backend pairs line 1 with line 1, line 2 with line 2, and so on.
3. Each pair is stored in ChromaDB as a proverb record.
4. When a user asks a question, the system retrieves the closest proverb records.
5. If a relevant record exists, the tutor answers in simple Myanmar.
6. If nothing relevant exists, the tutor returns the standard not-found response.

## Dataset Format

Use two `.docx` files. Both files must have the same number of non-empty paragraphs.

`proverbs.docx`

```text
ဆရာ့ထက် တပည့်လက်စောင်းထက်
ကုသိုလ်လည်းရ၊ ဝမ်းလည်းဝ
```

`meanings.docx`

```text
တပည့်ဖြစ်သူ၏ ပညာအရည်အသွေးက ဆရာ့ထက် အစွမ်းထက်မြက်နေခြင်းကို ဆိုလိုပါသည်။
အသက်မွေးဝမ်းကျောင်းပြုရာ၌ ဝမ်းရေးအတွက် ဝင်ငွေရရှိရုံမျှမကဘဲ သူတစ်ပါးကို အကျိုးပြုသဖြင့် ကုသိုလ်ပါရရှိခြင်းကို ဆိုလိုသည်။
```

The first proverb maps to the first meaning, the second proverb maps to the second meaning.

## Environment

Copy the example env file:

```bash
cd backend
cp .env.example .env
```

Required values include:

- `MONGODB_URI`
- `JWT_SECRET_KEY`
- `OLLAMA_BASE_URL`
- `OLLAMA_MODEL`
- `CHROMA_PERSIST_DIR`
- `CHROMA_COLLECTION_NAME`

## Run Locally

From the repo root:

```bash
cd backend
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Start Ollama and pull the model:

```bash
ollama pull qwen3
```

Run the API:

```bash
uvicorn app.main:app --reload
```

Open:

```text
http://127.0.0.1:8000/docs
```

Health check:

```text
GET /health
```

## API Overview

### Auth

- `POST /api/v1/register`
- `POST /api/v1/login`

### Chat

- `POST /api/v1/chat`
- `GET /api/v1/history`

### Dataset

- `POST /api/v1/import-docx`
- `POST /api/v1/reindex`
- `POST /api/v1/reindex/upload`
- `DELETE /api/v1/delete/file`

### Proverbs

- `POST /api/v1/proverbs`
- `PUT /api/v1/proverbs/{proverb_id}`

## Authentication

Most API routes require a bearer token:

```http
Authorization: Bearer <access_token>
```

Admin-only routes include:

- `POST /api/v1/import-docx`
- `POST /api/v1/proverbs`
- `PUT /api/v1/proverbs/{proverb_id}`

## API Examples

### Register

```http
POST /api/v1/register
Content-Type: application/json
```

```json
{
  "email": "admin@example.com",
  "password": "StrongPass123",
  "name": "Admin"
}
```

### Login

```http
POST /api/v1/login
Content-Type: application/json
```

```json
{
  "email": "admin@example.com",
  "password": "StrongPass123"
}
```

Response:

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

### Import Word Dataset

```http
POST /api/v1/import-docx
Authorization: Bearer <admin_token>
Content-Type: multipart/form-data
```

Form fields:

- `proverbs_file`: `proverbs.docx`
- `meanings_file`: `meanings.docx`

Response:

```json
{
  "inserted": 120,
  "skipped": 0,
  "warnings": [],
  "collection": "proverbs"
}
```

If the two files do not have the same number of non-empty paragraphs:

```json
{
  "detail": "Proverbs and meanings count must match: proverbs=120 meanings=119"
}
```

### Reindex From Uploaded Word Files

Use this when you want to rebuild the collection from uploaded files.

```http
POST /api/v1/reindex/upload
Content-Type: multipart/form-data
```

Form fields:

- `proverbs_file`: `proverbs.docx`
- `meanings_file`: `meanings.docx`
- `clear_existing`: `true`

### Delete Chroma Dataset Files

```http
DELETE /api/v1/delete/file
```

Response:

```json
{
  "ok": true,
  "deleted": true,
  "message": "Chroma dataset files deleted."
}
```

### Ask A Proverb Question

```http
POST /api/v1/chat
Authorization: Bearer <token>
Content-Type: application/json
```

```json
{
  "message": "မောင်မောင်သည် သူ၏ ဆရာထက် တော်နေရင် ဘယ်လိုစကားပုံရှိသလဲ။"
}
```

Response:

```json
{
  "answer": {
    "proverb": "ဆရာ့ထက် တပည့်လက်စောင်းထက်",
    "meaning_simple_mm": "ကလေးတို့ရေ၊ တပည့်က ကြိုးစားလို့ ဆရာထက် ပိုတော်လာတဲ့အခါ ဒီစကားပုံကို သုံးတာပါ။",
    "example_mm": null
  }
}
```

### Ask For Meaning

```json
{
  "message": "ဆရာ့ထက် တပည့်လက်စောင်းထက် ကဘာကိုဆိုလိုတာလဲ"
}
```

Response:

```json
{
  "answer": {
    "proverb": "ဆရာ့ထက် တပည့်လက်စောင်းထက်",
    "meaning_simple_mm": "ကလေးတို့ရေ၊ တပည့်က ကြိုးစားလို့ ဆရာထက် ပိုတော်လာတဲ့အခါ ဒီစကားပုံကို သုံးတာပါ။",
    "example_mm": null,
    "sources": [
      {
        "keyword": null,
        "proverb": "ဆရာ့ထက် တပည့်လက်စောင်းထက်",
        "meaning": "တပည့်ဖြစ်သူ၏ ပညာအရည်အသွေးက ဆရာ့ထက် အစွမ်းထက်မြက်နေခြင်းကို ဆိုလိုပါသည်။",
        "example": null,
        "score": 0.0
      }
    ]
  }
}
```

### Ask About The System

```json
{
  "message": "မင်းကဘယ်သူလဲ။ ဒီ system ကဘာအလုပ်လုပ်သလဲ။"
}
```

Response:

```json
{
  "answer": {
    "proverb": null,
    "meaning_simple_mm": "ကလေးတို့ရေ၊ ကျွန်ုပ်က မြန်မာစကားပုံတွေကို ရှာပေးပြီး အဓိပ္ပါယ်ကို လွယ်လွယ်ကူကူ ရှင်းပြပေးတဲ့ Myanmar Proverbs AI Tutor ပါ။ ဒီစနစ်က မေးခွန်းနဲ့ သက်ဆိုင်တဲ့ စကားပုံကို ဒေတာထဲကနေ ရှာပြီး ဆရာတစ်ယောက်လို နားလည်လွယ်အောင် ပြန်ဖြေပေးတာပါ။",
    "example_mm": null,
    "sources": []
  }
}
```

### Not Found

If the proverb is not in the dataset or the question is unrelated:

```json
{
  "answer": {
    "proverb": null,
    "meaning_simple_mm": "ဝမ်းနည်းပါတယ်။ ကျွန်ုပ်၏ စကားပုံဒေတာအတွင်း မတွေ့ရှိပါ။",
    "example_mm": null,
    "sources": []
  }
}
```

## Myanmar Matching Notes

The retriever includes Myanmar-friendly matching for common user input differences:

- `ဆရာ့ထက်` can match `ဆရာထက်`
- `တပည့်` can match `တပည့်`
- joined words are compacted for comparison
- punctuation is ignored
- selected synonym groups are considered, such as:
  - `တော်`, `ထူးချွန်`, `ထက်မြက်`
  - `ကဲ့ရဲ့`, `အပြစ်တင်`, `ဝေဖန်`
  - `ဆရာ`, `ဆရာ့`
  - `တပည့်`, `ကျောင်းသား`

This helps retrieval, but the dataset still matters. If a proverb does not exist in ChromaDB, the system should not invent it.

## Tests And Checks

Run guardrail tests:

```bash
cd backend
python test_guardrails.py
```

Run semantic search checks:

```bash
cd backend
python test_semantic_search.py
```

Quick import check:

```bash
cd backend
PYTHONDONTWRITEBYTECODE=1 python -c "import app.services.rag; print('ok')"
```

## Deployment Notes

The included `render.yaml` runs the backend with:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

For deployment, configure at least:

- MongoDB connection
- JWT secret
- Ollama base URL and model
- Chroma persistence path

ChromaDB persistence is local unless you attach persistent storage. For production scaling, use persistent disk or a managed vector database.

## Railway Deployment

Railway can host the FastAPI backend so your frontend can call it from any language or framework.

1. Push this repo to GitHub.
2. In Railway, create a new project from the GitHub repo.
3. Set the root directory to `backend`.
4. Use this start command:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

5. Add these environment variables in Railway:

```text
ENVIRONMENT=production
MONGODB_URI=your-mongodb-connection-string
JWT_SECRET_KEY=your-long-random-secret
OLLAMA_BASE_URL=your-ollama-url
OLLAMA_MODEL=qwen3:latest
CHROMA_PERSIST_DIR=./chroma_data
CHROMA_COLLECTION_NAME=proverbs
ALLOWED_ORIGINS=https://your-frontend-domain.com
```

6. Deploy, then copy the Railway public URL, for example `https://your-app.up.railway.app`.
7. In your frontend, set the API base URL to that Railway URL.

Important notes:

- `ALLOWED_ORIGINS` must include your frontend domain, or browser requests will be blocked by CORS.
- `Ollama` at `http://localhost:11434` will not work on Railway. Use a reachable Ollama service or another hosted model endpoint.
- `CHROMA_PERSIST_DIR` on Railway is temporary unless you attach persistent storage. If you need the proverb data to survive redeploys, use Railway volumes or another persistent vector store.

## Troubleshooting

### The answer is not found, but I know the proverb exists

Check:

- Was the correct `.docx` dataset imported?
- Do both Word files have the same number of non-empty paragraphs?
- Does the proverb exist in ChromaDB?
- Did you delete Chroma data with `DELETE /api/v1/delete/file` and forget to reimport?

### The answer is wrong

Check:

- The expected proverb may be missing from the current Chroma collection.
- The user wording may need a new synonym group.
- The source meaning may need clearer keywords or better wording.

### File import fails

Check:

- Both uploads must be `.docx`.
- Both files are required in the same request.
- The number of non-empty paragraphs must match.
