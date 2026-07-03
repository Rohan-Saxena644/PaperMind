# PaperMind — AI Research Workspace

Upload research papers, get AI-generated summaries, flashcards, and ask questions across your entire library.

## Stack

| Layer | Tech |
|---|---|
| Backend API | FastAPI (Python) |
| Background Worker | Redis Queue + custom worker |
| Database | PostgreSQL (SQLAlchemy + Alembic) |
| Vector Store | Qdrant |
| Knowledge Graph | Neo4j + networkx |
| AI | Gemini 2.5 Flash + text-embedding-004 |
| PDF Processing | PyMuPDF |
| Frontend | Next.js (coming next) |
| Infra | Docker Compose |

## Getting Started

### 1. Clone and configure

```bash
cp backend/.env.example backend/.env
# Edit backend/.env and add your GEMINI_API_KEY
```

Get your free Gemini API key at: https://aistudio.google.com/apikey

Optional Google OAuth setup:
- Create OAuth credentials in Google Cloud Console.
- Add this authorized redirect URI: `http://localhost:8000/api/v1/auth/google/callback`
- Set `GOOGLE_OAUTH_CLIENT_ID` and `GOOGLE_OAUTH_CLIENT_SECRET` in `backend/.env`.

### 2. Start all services

```bash
docker-compose up --build
```

This starts:
- FastAPI backend at http://localhost:8000
- Background worker (processes uploaded papers)
- PostgreSQL at localhost:5432
- Redis at localhost:6379
- Qdrant at http://localhost:6333
- Neo4j at http://localhost:7474

### 3. View API docs

Open http://localhost:8000/docs for interactive Swagger UI.

## API Overview

### Auth
- `POST /api/v1/auth/register` — create account
- `POST /api/v1/auth/login` — get JWT token
- `GET /api/v1/auth/me` — current user
- `GET /api/v1/auth/google/start` - start Google OAuth login
- `GET /api/v1/auth/google/callback` - Google OAuth callback

### Papers
- `POST /api/v1/papers/upload` — upload PDF (returns immediately, processes in background)
- `POST /api/v1/papers/ingest-url` - import a readable webpage or YouTube video transcript
- `GET /api/v1/papers/` — list all your papers
- `GET /api/v1/papers/{id}` — get paper details + AI content
- `DELETE /api/v1/papers/{id}` — delete paper + embeddings

### Chat (RAG)
- `POST /api/v1/chats/` — create a chat session
- `GET /api/v1/chats/` — list chats
- `POST /api/v1/chats/{id}/ask` — ask a question (searches all papers)
- `GET /api/v1/chats/{id}` — get chat history

### Knowledge Graph
- `GET /api/v1/graph/knowledge-map` - graph across your full library
- `GET /api/v1/graph/papers/{paper_id}` - graph for one paper
- `GET /api/v1/graph/insights` - node counts, research threads, density, and top concepts

## How paper processing works

```
Upload PDF
    ↓
Saved to disk, DB record created (status: pending)
    ↓
Job enqueued in Redis
    ↓ (background worker picks it up)
Extract text with PyMuPDF
    ↓
Chunk text (1000 chars, 200 overlap)
    ↓
Gemini generates: title, summary, key contributions, keywords
    ↓
Gemini generates 10 flashcards
    ↓
Each chunk embedded with text-embedding-004
    ↓
Embeddings stored in Qdrant
    ↓
Gemini extracts concepts and authors
    ↓
Paper/Concept/Author graph written to Neo4j
    ↓
Status: ready
```

URL ingestion follows the same processing pipeline after extracting readable text. YouTube imports require a public transcript/captions track.

## Project Structure

```
papermind/
├── docker-compose.yml
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app
│   │   ├── api/
│   │   │   ├── deps.py          # Auth dependency
│   │   │   └── routes/
│   │   │       ├── auth.py
│   │   │       ├── papers.py
│   │   │       └── chat.py
│   │   ├── core/
│   │   │   ├── config.py        # Settings (pydantic-settings)
│   │   │   └── security.py      # JWT + bcrypt
│   │   ├── db/
│   │   │   └── session.py       # SQLAlchemy session
│   │   ├── models/
│   │   │   └── models.py        # DB models
│   │   ├── schemas/
│   │   │   └── schemas.py       # Pydantic schemas
│   │   ├── services/
│   │   │   ├── ai/
│   │   │   │   ├── gemini.py    # Gemini API calls
│   │   │   │   └── vector_store.py  # Qdrant operations
│   │   │   └── ingestion/
│   │   │       └── pdf_processor.py  # PDF → chunks
│   │   └── workers/
│   │       └── processor.py     # Background job runner
│   └── requirements.txt
└── frontend/                    # Next.js (next phase)
```
