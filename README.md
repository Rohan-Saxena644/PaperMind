# PaperMind

PaperMind is an AI research workspace for uploading papers, organizing research into workspaces, generating summaries and flashcards, asking RAG questions across a workspace, comparing papers, reviewing quizzes, and exploring a knowledge graph of concepts.

## Current Status

PaperMind is MVP-complete locally and ready for deployment preparation.

Built features:

- Email/password auth with JWT sessions.
- Optional Google OAuth login.
- Workspace-scoped research areas, so unrelated topics stay isolated.
- PDF upload and background ingestion.
- URL, YouTube transcript, and arXiv ingestion.
- AI summaries, keywords, key contributions, and flashcards.
- RAG chat over the selected workspace.
- Paper comparison for 2-4 papers.
- Quiz mode with spaced repetition review state.
- Reading progress, personal notes, and highlights.
- Timeline view by publication year.
- Neo4j knowledge graph with backend-computed networkx layout and graph insights.
- Worker retries, dead-letter style failure state, and visible processing errors.
- Gemini free-tier aware rate limiting, caching, and smaller prompts/context windows.

## Stack

| Layer | Tech |
| --- | --- |
| Backend API | FastAPI, SQLAlchemy, Pydantic |
| Frontend | Next.js, TypeScript, Tailwind CSS |
| Auth | JWT, bcrypt, optional Google OAuth |
| Worker | Redis queue + custom Python worker |
| Relational DB | PostgreSQL |
| Vector DB | Qdrant |
| Knowledge Graph | Neo4j |
| Graph Layout | networkx |
| AI Generation | Gemini 2.5 Flash |
| Embeddings | Gemini embedding model, `gemini-embedding-001` |
| PDF Processing | PyMuPDF |
| Infra | Docker Compose for local development |

## Local Setup

### 1. Configure environment files

```bash
cp backend/.env.example backend/.env
```

Edit `backend/.env` and set:

```env
GEMINI_API_KEY=your-gemini-api-key
SECRET_KEY=replace-this-before-production
```

Optional Google OAuth:

```env
GOOGLE_OAUTH_CLIENT_ID=your-client-id
GOOGLE_OAUTH_CLIENT_SECRET=your-client-secret
GOOGLE_OAUTH_REDIRECT_URI=http://localhost:8000/api/v1/auth/google/callback
```

For the frontend, create `frontend/.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 2. Start the full stack

```bash
docker compose up --build
```

Services:

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API docs: http://localhost:8000/docs
- PostgreSQL: localhost:5432
- Redis: localhost:6379
- Qdrant: http://localhost:6333
- Neo4j browser: http://localhost:7474

### 3. Run checks

Frontend build:

```bash
cd frontend
npm.cmd run build
cd ..
```

Backend syntax check:

```bash
python -c "import ast,pathlib; [ast.parse(p.read_text(encoding='utf-8'), filename=str(p)) for p in pathlib.Path('backend/app').rglob('*.py')]; print('ok')"
```

## How It Works

### Ingestion Pipeline

```text
Upload/import source
  -> create paper record in PostgreSQL
  -> enqueue Redis job
  -> worker extracts text
  -> chunk text with overlap
  -> Gemini generates metadata, summary, contributions, keywords
  -> Gemini generates flashcards
  -> embed chunks
  -> write embeddings to Qdrant with user_id + workspace_id filters
  -> extract concepts/authors
  -> write Paper/Concept/Author graph to Neo4j
  -> mark paper ready
```

PDFs use PyMuPDF. URL imports use readable webpage extraction. YouTube imports use public transcript/captions when available. arXiv imports search arXiv, download the selected PDF, and run the same ingestion pipeline.

### Workspace Isolation

Every major feature is scoped by the selected workspace:

- paper list
- uploads/imports
- chat retrieval
- comparisons
- quizzes
- timeline
- graph map and graph insights
- Qdrant vector filters
- Neo4j graph nodes and relationships

This means a healthcare research workspace and an engine design workspace can coexist without polluting each other's retrieval context.

### RAG Chat

When a user asks a question:

1. The question is embedded.
2. Qdrant retrieves the top relevant chunks for the current user and workspace.
3. Optional selected-paper filtering narrows retrieval further.
4. Gemini answers using only retrieved context.
5. Sources are returned with the answer.

### Knowledge Graph

The worker asks Gemini to extract concepts, authors, and concept relationships. Neo4j stores:

- `Paper`
- `Concept`
- `Author`
- `WRITTEN_BY`
- `INTRODUCES`
- `USES`
- `RELATED_TO`

The backend computes graph layout and analytics using networkx:

- spring layout coordinates
- degree centrality
- connected components
- density
- top foundational concepts

The frontend only renders precomputed graph coordinates.

## API Overview

### Auth

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`
- `GET /api/v1/auth/google/start`
- `GET /api/v1/auth/google/callback`

### Workspaces

- `GET /api/v1/workspaces/`
- `POST /api/v1/workspaces/`
- `PATCH /api/v1/workspaces/{workspace_id}`
- `DELETE /api/v1/workspaces/{workspace_id}`

Clients send the active workspace with:

```http
X-Workspace-Id: <workspace-id>
```

If omitted, the backend uses or creates the user's default workspace.

### Papers

- `POST /api/v1/papers/upload`
- `POST /api/v1/papers/ingest-url`
- `GET /api/v1/papers/arxiv/search`
- `POST /api/v1/papers/arxiv/import`
- `GET /api/v1/papers/`
- `GET /api/v1/papers/{paper_id}`
- `PATCH /api/v1/papers/{paper_id}/reading-progress`
- `POST /api/v1/papers/{paper_id}/retry`
- `DELETE /api/v1/papers/{paper_id}`

### Chat

- `POST /api/v1/chats/`
- `GET /api/v1/chats/`
- `GET /api/v1/chats/{chat_id}`
- `POST /api/v1/chats/{chat_id}/ask`
- `DELETE /api/v1/chats/{chat_id}`

### Compare, Quiz, Graph, Timeline

- `POST /api/v1/compare/`
- `GET /api/v1/quiz/random`
- `POST /api/v1/quiz/review`
- `GET /api/v1/graph/knowledge-map`
- `GET /api/v1/graph/papers/{paper_id}`
- `GET /api/v1/graph/insights`
- `GET /api/v1/timeline/`

## Gemini Free-Tier Notes

The app is designed to be careful with Gemini free-tier limits:

- AI requests are rate-limited.
- Daily request caps can be configured.
- Repeated generation/embedding calls are cached in Redis.
- Chat context is trimmed before generation.
- Worker retries use exponential backoff.
- Ingestion fails visibly instead of looping forever.

For real production usage, paid Gemini limits or another provider may be needed. Switching generation providers is possible, but embeddings and stored vector dimensions must be handled carefully.

## Deployment Plan

Recommended split:

- Frontend: Vercel
- Backend API: Render web service, Fly.io, Railway, or a VPS
- Worker: separate Render background worker, Fly machine, Railway worker, or VPS process
- PostgreSQL: managed Postgres
- Redis: managed Redis
- Qdrant: Qdrant Cloud or self-hosted container
- Neo4j: Neo4j Aura or self-hosted container

Vercel is a good fit for the frontend. The backend is not a single-service app because it depends on a persistent worker, Redis, Postgres, Qdrant, and Neo4j. For the simplest production deployment, use managed databases for Postgres, Redis, Qdrant, and Neo4j, then deploy only the backend API and worker as app services.

Production environment checklist:

```env
SECRET_KEY=strong-random-secret
DEBUG=false
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
QDRANT_URL=https://...
QDRANT_COLLECTION=papermind_papers
NEO4J_URI=neo4j+s://...
NEO4J_USER=neo4j
NEO4J_PASSWORD=...
GEMINI_API_KEY=...
GEMINI_MODEL=gemini-2.5-flash
GEMINI_EMBEDDING_MODEL=gemini-embedding-001
FRONTEND_URL=https://your-frontend-domain
BACKEND_URL=https://your-backend-domain
GOOGLE_OAUTH_CLIENT_ID=...
GOOGLE_OAUTH_CLIENT_SECRET=...
GOOGLE_OAUTH_REDIRECT_URI=https://your-backend-domain/api/v1/auth/google/callback
```

Frontend production environment:

```env
NEXT_PUBLIC_API_URL=https://your-backend-domain
```

## Project Structure

```text
papermind/
  docker-compose.yml
  backend/
    Dockerfile
    requirements.txt
    app/
      main.py
      api/
        deps.py
        routes/
          auth.py
          chat.py
          compare.py
          graph.py
          papers.py
          timeline.py
          workspaces.py
      core/
        config.py
        security.py
      db/
        session.py
      models/
        models.py
      schemas/
        schemas.py
      services/
        ai/
          gemini.py
          graph.py
          graph_layout.py
          vector_store.py
        ingestion/
          arxiv_processor.py
          pdf_processor.py
          text_processor.py
          url_processor.py
      workers/
        processor.py
  frontend/
    Dockerfile
    package.json
    src/
      app/
      components/
      lib/
      types/
```

## Roadmap After Deployment

- Replace startup schema patching with proper Alembic migrations.
- Add production object storage for uploaded files.
- Add observability for worker failures, AI rate limits, and latency.
- Add automated backend route tests.
- Add evaluation sets for RAG answer quality.
- Improve section-aware PDF chunking.
- Add more advanced graph exploration queries.
