# 🇲🇲 Myanmar Proverbs AI Tutor

An AI-powered Retrieval-Augmented Generation (RAG) system that helps users understand Myanmar proverbs through natural language conversations.

Built with FastAPI, ChromaDB, MongoDB, and Ollama, the system retrieves proverb knowledge from a curated dataset and explains meanings in simple, educational Myanmar language.

---

## ✨ Features

* 📚 Myanmar Proverbs Knowledge Base
* 🤖 AI-powered Question Answering (RAG)
* 🔍 Semantic Search with ChromaDB
* 🇲🇲 Myanmar Language Optimized Retrieval
* 📄 DOCX Dataset Import Support
* 🔐 JWT Authentication & Role-Based Access Control
* 👨‍💼 Admin Dataset Management
* 💬 Chat History Storage
* 🚫 Hallucination Prevention Guardrails
* ⚡ FastAPI REST API

---

## 🏗️ System Architecture

```text
User Question
      │
      ▼
 FastAPI API
      │
      ▼
 Semantic Search
   (ChromaDB)
      │
      ▼
 Relevant Proverbs
      │
      ▼
 Ollama / Qwen
      │
      ▼
 AI Generated Answer
```

---

## 🛠️ Technology Stack

| Category        | Technology    |
| --------------- | ------------- |
| Backend         | FastAPI       |
| Vector Database | ChromaDB      |
| Database        | MongoDB       |
| LLM             | Ollama + Qwen |
| Authentication  | JWT           |
| Validation      | Pydantic      |
| File Processing | python-docx   |

---

## 📂 Project Structure

```text
backend/
├── app/
│   ├── core/
│   ├── db/
│   ├── middleware/
│   ├── models/
│   ├── routers/
│   ├── services/
│   └── main.py
│
├── requirements.txt
├── .env.example
├── GUARDRAILS.md
├── SEMANTIC_SEARCH_GUIDE.md
├── test_guardrails.py
└── test_semantic_search.py
```

---

## 🚀 Getting Started

### 1. Clone Repository

```bash
git clone https://github.com/yourusername/myanmar-proverbs-ai-tutor.git

cd myanmar-proverbs-ai-tutor/backend
```

### 2. Create Virtual Environment

```bash
python -m venv .venv
```

### Windows

```powershell
.\.venv\Scripts\Activate.ps1
```

### Linux / Mac

```bash
source .venv/bin/activate
```

---

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

### 4. Configure Environment

```bash
cp .env.example .env
```

Required variables:

```env
MONGODB_URI=
JWT_SECRET_KEY=
OLLAMA_BASE_URL=
OLLAMA_MODEL=
CHROMA_PERSIST_DIR=
CHROMA_COLLECTION_NAME=
```

---

### 5. Pull LLM Model

```bash
ollama pull qwen3
```

---

### 6. Run Application

```bash
uvicorn app.main:app --reload
```

API Documentation:

```text
http://localhost:8000/docs
```

---

## 📄 Dataset Format

The system imports two DOCX files:

### Proverbs

```text
ဆရာ့ထက် တပည့်လက်စောင်းထက်
ကုသိုလ်လည်းရ၊ ဝမ်းလည်းဝ
```

### Meanings

```text
တပည့်ဖြစ်သူ၏ ပညာအရည်အသွေးက ဆရာ့ထက် ပိုမိုထက်မြက်နေခြင်းကို ဆိုလိုပါသည်။
အသက်မွေးဝမ်းကျောင်းပြုရာ၌ ကုသိုလ်နှင့် ဝင်ငွေ နှစ်မျိုးလုံး ရရှိခြင်းကို ဆိုလိုသည်။
```

Each proverb is matched with the corresponding meaning based on paragraph order.

---

## 🔐 Authentication

Protected endpoints require JWT access tokens.

```http
Authorization: Bearer <token>
```

Admin-only operations:

* Import Dataset
* Reindex Collection
* Manage Proverbs
* Delete Dataset

---

## 📡 API Endpoints

### Authentication

| Method | Endpoint  |
| ------ | --------- |
| POST   | /register |
| POST   | /login    |

### Chat

| Method | Endpoint |
| ------ | -------- |
| POST   | /chat    |
| GET    | /history |

### Dataset

| Method | Endpoint        |
| ------ | --------------- |
| POST   | /import-docx    |
| POST   | /reindex        |
| POST   | /reindex/upload |
| DELETE | /delete/file    |

### Proverbs

| Method | Endpoint       |
| ------ | -------------- |
| POST   | /proverbs      |
| PUT    | /proverbs/{id} |

---

## 🛡️ Guardrails

The system follows strict retrieval rules:

✅ Relevant proverb found → Answer returned

✅ Meaning request → Meaning explained

✅ System-related question → Tutor explanation

❌ Unrelated question → Not Found

❌ Missing proverb → Not Found

This prevents hallucinated answers.

---

## 🧪 Testing

Run Guardrail Tests:

```bash
python test_guardrails.py
```

Run Semantic Search Tests:

```bash
python test_semantic_search.py
```

---

## 🚀 Deployment

Supported platforms:

* Railway
* Render
* VPS
* Docker

Production requirements:

* MongoDB
* Ollama Server
* Persistent Chroma Storage
* Environment Variables

---

## 🔮 Future Improvements

* Voice Input (Speech-to-Text)
* Telegram Bot Integration
* Multi-LLM Support
* Example Generation
* User Feedback Collection
* Advanced Semantic Ranking
* Fine-Tuned Myanmar Embedding Models

---

## 👨‍💻 Author

**Zarni Maung**

Final Year Computer Science Student

Polytechnic University (Myeik)

GitHub: https://github.com/zaenimaung1

---

## 📜 License

This project is licensed under the MIT License.
