# NileConnect AI Contact Center — Local Setup & Run Guide (Phase 1 + 2 AI)

## Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Python | 3.11+ | https://python.org |
| PostgreSQL | 14+ | https://www.postgresql.org |
| pip | latest | included with Python |

---

## Step 1 — PostgreSQL: Create the Database

Open **pgAdmin** or **psql** and run:

```sql
CREATE DATABASE nileconnect;
```

Then apply the schema:

```bash
psql -U postgres -d nileconnect -f database/schema.sql
```

To load demo seed data (recommended for testing):

```bash
psql -U postgres -d nileconnect -f database/seed.sql
```

---

## Step 2 — Backend: Install and Configure

```powershell
cd d:\Work\NileConnect_AI_Contact_Center\backend

python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

> **Note:** `requirements.txt` is the **lean backend-only** file (FastAPI,
> SQLAlchemy, auth, etc.). AI packages are intentionally excluded from it
> and live in `ai_requirements.txt` / `ai_venv` instead.

Edit `backend/.env` — update the DATABASE_URL with your PostgreSQL password:

```
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/nileconnect
```

Also set your AI API keys in `backend/.env`:

```
GROQ_API_KEY=your_groq_api_key
TAVILY_API_KEY=your_tavily_api_key
```

---

## Step 3 — AI Environment: Install (Phase 2)

The AI engine runs in a **separate dedicated venv** to isolate heavy ML
dependencies (torch, sentence-transformers, faiss) from the main backend.

```powershell
cd d:\Work\NileConnect_AI_Contact_Center\backend

# The venv already exists and all packages are installed:
.\ai_venv\Scripts\Activate.ps1
pip install -r ai_requirements.txt
```

> **Status:** `ai_venv\` and `ai_requirements.txt` are both present in
> `backend/`. **All packages including `groq 1.6.0` were installed
> successfully on 2026-08-15.** Re-run `pip install -r ai_requirements.txt`
> only if you add new packages or set up on a new machine.

**Packages installed in `ai_venv`:**

| Package | Purpose |
|---|---|
| `groq` | Groq LLM API client |
| `tavily-python` | Web search tool |
| `langchain-core` | Tool wrappers / schemas |
| `sentence-transformers` | Local text embeddings |
| `faiss-cpu` | Vector similarity store |
| `pypdf` | PDF text extraction |
| `numpy` | Numerical operations |
| `psycopg2-binary` | PostgreSQL access from AI tools |
| `python-dotenv` | `.env` config loading |
| `pydantic` / `pydantic-settings` | Schema validation & settings |

**To activate the AI venv manually:**

```powershell
cd d:\Work\NileConnect_AI_Contact_Center\backend
.\ai_venv\Scripts\Activate.ps1
```

---

## Step 4 — Run the Backend

```powershell
cd d:\Work\NileConnect_AI_Contact_Center\backend
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Verify it works:
- Interactive API docs: http://localhost:8000/docs
- Health check:        http://localhost:8000/api/v1/health
- AI Assistant API:    http://localhost:8000/api/v1/ai/ask

NOTE: On first run, FastAPI auto-creates all database tables via SQLAlchemy create_all().

---

## Step 5 — Frontend: Install and Run

Open a NEW terminal:

```powershell
cd d:\Work\NileConnect_AI_Contact_Center\frontend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py --server.port 8501
```

Streamlit opens at: http://localhost:8501

---

## Demo Credentials

| Role  | Email                          | Password  |
|-------|--------------------------------|-----------|
| Admin | admin@nileconnect.eg           | Admin@123 |
| Agent | sara.hassan@nileconnect.eg     | Agent@123 |
| Agent | omar.nabil@nileconnect.eg      | Agent@123 |

These are loaded from database/seed.sql.

### Creating First Admin Without Seed Data

Use psql to insert an admin directly:

```sql
INSERT INTO users (name, email, password_hash, role, is_active)
VALUES (
  'Admin',
  'admin@nileconnect.eg',
  '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW',
  'ADMIN',
  true
);

INSERT INTO users (name, email, password_hash, role, is_active)
VALUES (
  'Admin',
  'admin@nileconnects.eg',
  '$2b$12$ZWywfJgijhtZfinqA5jHIOseFmSZJVocHZ6WV41aQli1sv3lxjlVW',
  'ADMIN',
  true
);

-- Password above is bcrypt hash of: Admin@123
```

---

## Phase 1 Test Checklist

### Authentication
- [ ] Login as Admin -> Admin Dashboard
- [ ] Login as Agent -> Agent Dashboard
- [ ] Wrong password -> error message
- [ ] Logout -> back to login

### Customer Management
- [ ] Create customer (name + phone)
- [ ] Duplicate phone -> conflict error
- [ ] Search by name / phone
- [ ] Edit customer

### Case Management
- [ ] Create case linked to customer
- [ ] Case status = OPEN by default
- [ ] Update status to IN_PROGRESS, RESOLVED
- [ ] Agent only sees own cases
- [ ] Admin sees all cases

### Call Management
- [ ] Record INBOUND_HUMAN call
- [ ] Call appears in history
- [ ] Filter calls by case

### Follow-up Scheduling
- [ ] Schedule follow-up for a case
- [ ] Case status -> AI_FOLLOW_UP_SCHEDULED
- [ ] Update follow-up result YES/NO

### Document Management (Admin)
- [ ] Upload PDF document
- [ ] Document listed with status READY
- [ ] Agent cannot upload (backend returns 403)
- [ ] Delete document

### Reports and Audit (Admin)
- [ ] Reports show correct counts and charts
- [ ] Audit Logs page loads
- [ ] Agent cannot access Reports page

### Users Management (Admin)
- [ ] Create new Call Center Agent
- [ ] Disable a user (is_active = false)
- [ ] Disabled user cannot login

---

## Project Structure

```
NileConnect_AI_Contact_Center/
|-- backend/
|   |-- .env                    <- your local config (copy from .env.example)
|   |-- requirements.txt        <- backend dependencies
|   |-- ai_requirements.txt     <- AI-only dependencies (Phase 2)
|   |-- venv/                   <- backend virtual environment
|   |-- ai_venv/                <- AI dedicated virtual environment ✅ installed
|   +-- app/
|       |-- main.py             <- FastAPI entry point
|       |-- core/               <- config, db, security, logging
|       |-- models/             <- SQLAlchemy ORM models
|       |-- schemas/            <- Pydantic schemas
|       |-- repositories/       <- DB query layer
|       |-- services/           <- business logic
|       |-- api/routes/         <- HTTP route handlers
|       +-- ai/                 <- AI engine (Phase 2) ✅
|           |-- agent/          <- Agentic loop
|           |-- llm/            <- Groq LLM client
|           |-- rag/            <- RAG pipeline (FAISS + embeddings)
|           |-- tools/          <- SQL, RAG, web search tools
|           |-- memory/         <- conversation memory
|           |-- guardrails/     <- safety filters
|           +-- observability/  <- logging & tracing
|-- frontend/
|   |-- .env                    <- BACKEND_URL setting
|   |-- requirements.txt
|   |-- app.py                  <- Streamlit entry point
|   |-- config/                 <- settings
|   |-- utils/                  <- session, validators, formatters
|   |-- services/               <- API client wrappers
|   |-- components/             <- sidebar, cards, tables, alerts
|   +-- pages/                  <- all UI pages
+-- database/
    |-- schema.sql              <- DDL: tables + enums + indexes
    |-- seed.sql                <- demo data
    +-- init.sql                <- runs schema + seed
```

---

## Quick Troubleshooting

| Problem | Fix |
|---------|-----|
| Connection refused on backend | Check PostgreSQL is running and DATABASE_URL is correct |
| relation does not exist | Run schema.sql or restart backend (triggers create_all) |
| 401 Unauthorized in Streamlit | Token expired, logout and login again |
| Cannot connect to backend | Make sure uvicorn is running on port 8000 |
| Module not found in backend | Ensure venv is activated and you are in the backend/ directory |
| Seed passwords not working | Use exactly: Admin@123 / Agent@123 |
| passlib bcrypt error | pip install passlib[bcrypt]==1.7.4 |
| AI: GROQ_API_KEY not set | Add GROQ_API_KEY=... to backend/.env |
| AI: TAVILY_API_KEY not set | Add TAVILY_API_KEY=... to backend/.env |
| AI: ModuleNotFoundError (groq/faiss/etc) | Activate ai_venv, not the regular venv |
| AI: sentence-transformers slow on first run | Normal — model downloads on first use (~500 MB) |
| AI: faiss index not found | Upload at least one PDF via Knowledge Base first |
