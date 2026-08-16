# NileConnect AI Contact Center

## Frontend & Backend Architecture --- Phase 1

> **Project type:** AI-powered Telecom/ISP Contact Center\
> **Frontend:** Streamlit\
> **Backend:** FastAPI\
> **Database:** PostgreSQL\
> **Phase 1 scope:** Frontend + Backend + database + authentication +
> case/call management + document management\
> **Phase 2 scope:** Agentic RAG AI engine — Groq LLM + FAISS vector
> store + Tavily web search + SQL tool + RAG pipeline — fully
> implemented and installed in `backend/ai_venv`.

------------------------------------------------------------------------

## 1. Project Name

### Recommended GitHub repository

`nileconnect-ai-contact-center`

### Application name

**NileConnect AI Contact Center**

NileConnect is the fictional ISP/telecom company used for the demo
scenario.

------------------------------------------------------------------------

## 2. Business Scenario

A customer has a telecom/Internet problem and calls the company.

1.  A human Call Center Agent receives the real phone call.
2.  The agent creates or updates the customer's Case in the platform.
3.  The agent records the issue and call summary.
4.  The agent schedules an AI follow-up call.
5.  The AI outbound caller will later call the customer's real phone
    number and ask whether the issue was solved.
6.  If the customer answers YES, the Case becomes `RESOLVED`.
7.  If the customer answers NO, the Case becomes `NEEDS_HUMAN`.
8.  The human Call Center Agent calls the customer again.
9.  During the human follow-up, the Agent can later use the AI Assistant
    / Agentic RAG to retrieve customer history and company procedures.

Phase 1 does not implement the AI decision-making layer. It only
prepares the backend and frontend that the AI layer will use.

------------------------------------------------------------------------

# 3. High-Level Architecture

``` text
                         USER BROWSER
                              |
                              v
                    +-------------------+
                    | Streamlit Frontend|
                    +---------+---------+
                              |
                         HTTP / JSON
                              |
                              v
                    +-------------------+
                    |   FastAPI Backend |
                    +---------+---------+
                              |
          +-------------------+-------------------+
          |                   |                   |
          v                   v                   v
   Authentication       Case Management      Call Management
          |                   |                   |
          +-------------------+-------------------+
                              |
                              v
                       +-------------+
                       | PostgreSQL  |
                       +-------------+

                              |
                              v
                    +-------------------+
                    | Document Service  |
                    +---------+---------+
                              |
                              v
                     File Storage / KB

           AI Layer (Phase 2) ✅ Implemented
                              |
          +-------------------+-------------------+
          |                   |                   |
          v                   v                   v
    Agentic RAG          AI Tools            Web Search
  FAISS + Groq        SQL + PostgreSQL        Tavily
    (ai_venv)            (ai_venv)            (ai_venv)
```

------------------------------------------------------------------------

# 4. Roles

## Admin

The Admin manages the platform.

### Admin permissions

-   Manage Call Center users
-   View all customers
-   View all cases
-   View all calls
-   Upload company knowledge documents
-   Delete/re-index documents later
-   View reports
-   View audit logs
-   Manage system configuration

The Admin is responsible for the system and company knowledge.

------------------------------------------------------------------------

## Call Center Agent

The Call Center Agent is the operational user.

### Agent permissions

-   View assigned customers
-   Create customers
-   Create cases
-   Update cases
-   Record call summaries
-   View previous calls for accessible customers
-   Schedule follow-up calls
-   View AI follow-up results
-   Call the customer manually
-   Use the AI Assistant later

The Agent should not manage system-wide users, permissions, or global
configuration.

------------------------------------------------------------------------

# 5. Frontend Architecture --- Streamlit

``` text
frontend/
|
+-- app.py
|
+-- config/
|   +-- settings.py
|
+-- pages/
|   +-- login.py
|   +-- admin_dashboard.py
|   +-- agent_dashboard.py
|   +-- customers.py
|   +-- cases.py
|   +-- calls.py
|   +-- documents.py
|   +-- reports.py
|   +-- audit_logs.py
|
+-- components/
|   +-- sidebar.py
|   +-- navbar.py
|   +-- cards.py
|   +-- tables.py
|   +-- forms.py
|   +-- alerts.py
|
+-- services/
|   +-- api_client.py
|   +-- auth_service.py
|   +-- customer_service.py
|   +-- case_service.py
|   +-- call_service.py
|   +-- document_service.py
|
+-- utils/
|   +-- session.py
|   +-- validators.py
|   +-- formatters.py
|
+-- assets/
|
+-- requirements.txt
+-- Dockerfile
```

------------------------------------------------------------------------

# 6. Streamlit UI

## Login

``` text
+--------------------------------------+
|        NileConnect Contact Center    |
|                                      |
| Email                                |
| [____________________________]       |
|                                      |
| Password                             |
| [____________________________]       |
|                                      |
|              [ Login ]               |
+--------------------------------------+
```

After login, the frontend receives the user's role.

``` text
ADMIN
  -> Admin Dashboard

CALL_CENTER
  -> Agent Dashboard
```

------------------------------------------------------------------------

# 7. Admin Dashboard

``` text
Admin Dashboard
|
+-- Overview
|   +-- Total Customers
|   +-- Open Cases
|   +-- Resolved Cases
|   +-- Pending Follow-ups
|
+-- Users
|   +-- Call Center Agents
|   +-- Create Agent
|   +-- Disable Agent
|
+-- Customers
|
+-- Cases
|
+-- Calls
|
+-- Knowledge Base
|   +-- Upload Document
|   +-- Document List
|   +-- Processing Status
|
+-- Reports
|
+-- Audit Logs
```

------------------------------------------------------------------------

# 8. Call Center Dashboard

``` text
Agent Dashboard
|
+-- My Tasks
|   +-- New Cases
|   +-- Needs Human Follow-up
|   +-- Scheduled AI Follow-ups
|
+-- Customers
|
+-- Cases
|
+-- Calls
|
+-- Customer Details
|   +-- Profile
|   +-- Cases
|   +-- Previous Calls
|   +-- Follow-ups
|
+-- AI Assistant
|   [Phase 2]
```

------------------------------------------------------------------------

# 9. Customer Management UI

The customer does NOT need a login in the primary scenario.

The Call Center Agent creates the customer record.

``` text
Create Customer

Name:
[ Ahmed Mohamed ]

Phone:
[ 010xxxxxxxx ]

Email:
[ optional ]

[ Create Customer ]
```

------------------------------------------------------------------------

# 10. Case Management UI

``` text
Create Case

Customer:
[ Ahmed Mohamed ]

Issue:
[ Internet connection keeps disconnecting ]

Category:
[ Connectivity ]

Priority:
[ Medium ]

Description:
[ Customer reports repeated connection drops. ]

[ Create Case ]
```

Case status:

``` text
OPEN
IN_PROGRESS
FOLLOW_UP_PENDING
AI_FOLLOW_UP_SCHEDULED
AI_FOLLOW_UP_COMPLETED
NEEDS_HUMAN
RESOLVED
```

------------------------------------------------------------------------

# 11. Call Management UI

``` text
Call History

Customer: Ahmed Mohamed

------------------------------------------------
Date        Type             Outcome
------------------------------------------------
12 Aug      Human Inbound    Follow-up required
12 Aug      AI Follow-up     NO
13 Aug      Human Outbound   Pending
------------------------------------------------
```

Call types:

``` text
INBOUND_HUMAN
OUTBOUND_HUMAN
OUTBOUND_AI
```

------------------------------------------------------------------------

# 12. Document Management UI

Only authorized users, mainly Admins, manage the company Knowledge Base.

``` text
Knowledge Base

+----------------------------------------------+
| Upload Document                              |
|                                              |
| [ Choose PDF / DOCX ]       [ Upload ]       |
+----------------------------------------------+

Documents
------------------------------------------------
Name                         Status
------------------------------------------------
Internet_SOP.pdf             Ready
Router_Guide.pdf             Ready
Escalation_Policy.pdf        Processing
Customer_FAQ.docx            Ready
------------------------------------------------
```

The document processing pipeline is prepared for Phase 2:

``` text
PDF / DOCX
    |
    v
Text Extraction
    |
    v
Chunking
    |
    v
Embeddings
    |
    v
Vector Database
```

------------------------------------------------------------------------

# 13. Backend Architecture --- FastAPI

``` text
backend/
|
+-- app/
|   |
|   +-- main.py
|   |
|   +-- core/
|   |   +-- config.py
|   |   +-- security.py
|   |   +-- database.py
|   |   +-- logging.py
|   |
|   +-- api/
|   |   +-- dependencies.py
|   |   |
|   |   +-- routes/
|   |       +-- auth.py
|   |       +-- users.py
|   |       +-- customers.py
|   |       +-- cases.py
|   |       +-- calls.py
|   |       +-- documents.py
|   |       +-- reports.py
|   |       +-- audit_logs.py
|   |
|   +-- models/
|   |   +-- user.py
|   |   +-- customer.py
|   |   +-- case.py
|   |   +-- call.py
|   |   +-- ai_followup.py
|   |   +-- document.py
|   |   +-- audit_log.py
|   |
|   +-- schemas/
|   |   +-- auth.py
|   |   +-- user.py
|   |   +-- customer.py
|   |   +-- case.py
|   |   +-- call.py
|   |   +-- ai_followup.py
|   |   +-- document.py
|   |
|   +-- services/
|   |   +-- auth_service.py
|   |   +-- user_service.py
|   |   +-- customer_service.py
|   |   +-- case_service.py
|   |   +-- call_service.py
|   |   +-- followup_service.py
|   |   +-- document_service.py
|   |   +-- report_service.py
|   |
|   +-- repositories/
|   |   +-- user_repository.py
|   |   +-- customer_repository.py
|   |   +-- case_repository.py
|   |   +-- call_repository.py
|   |   +-- document_repository.py
|   |
|   +-- workers/
|       +-- scheduler.py
|       +-- tasks.py
|   +-- ai/                      <- AI engine (Phase 2) ✅
|       +-- agent/               <- Agentic loop
|       +-- llm/                 <- Groq LLM client
|       +-- rag/                 <- FAISS RAG pipeline
|       +-- tools/               <- SQL, RAG, web search tools
|       +-- memory/              <- conversation memory
|       +-- guardrails/          <- safety filters
|       +-- observability/       <- logging & tracing
|
+-- tests/
|
+-- requirements.txt          <- backend-only packages (no AI deps)
+-- ai_requirements.txt       <- AI-only packages (Phase 2) ✅
+-- Dockerfile
+-- .env.example
```

------------------------------------------------------------------------

# 14. Backend Layers

Use a clean separation:

``` text
HTTP Request
     |
     v
Router
     |
     v
Schema Validation
     |
     v
Service Layer
     |
     v
Repository
     |
     v
PostgreSQL
```

Example:

``` text
POST /api/v1/cases
        |
        v
cases.py
        |
        v
case_service.py
        |
        v
case_repository.py
        |
        v
PostgreSQL
```

This keeps the FastAPI routes thin and makes the project easier to
extend when the AI layer is added.

------------------------------------------------------------------------

# 15. PostgreSQL Database

## users

``` text
id
name
email
password_hash
role
is_active
created_at
```

Roles:

``` text
ADMIN
CALL_CENTER
```

------------------------------------------------------------------------

## customers

``` text
id
name
phone
email
created_at
updated_at
```

------------------------------------------------------------------------

## cases

``` text
id
customer_id
assigned_agent_id
issue
category
description
priority
status
created_at
updated_at
resolved_at
```

Relationships:

``` text
Customer 1 ---- N Cases
Agent    1 ---- N Cases
```

------------------------------------------------------------------------

## calls

``` text
id
customer_id
case_id
agent_id
call_type
started_at
ended_at
duration
summary
outcome
transcript
created_at
```

------------------------------------------------------------------------

## ai_followups

``` text
id
case_id
customer_id
scheduled_at
status
attempt_number
result
call_id
created_at
completed_at
```

------------------------------------------------------------------------

## documents

``` text
id
filename
file_type
storage_path
uploaded_by
status
created_at
updated_at
```

------------------------------------------------------------------------

## audit_logs

``` text
id
user_id
action
entity_type
entity_id
details
created_at
```

------------------------------------------------------------------------

# 16. Main API Endpoints

## Authentication

``` text
POST /api/v1/auth/login
GET  /api/v1/auth/me
POST /api/v1/auth/logout
```

## Users

``` text
GET    /api/v1/users
POST   /api/v1/users
GET    /api/v1/users/{id}
PATCH  /api/v1/users/{id}
DELETE /api/v1/users/{id}
```

## Customers

``` text
GET  /api/v1/customers
POST /api/v1/customers
GET  /api/v1/customers/{id}
PATCH /api/v1/customers/{id}
```

## Cases

``` text
GET  /api/v1/cases
POST /api/v1/cases
GET  /api/v1/cases/{id}
PATCH /api/v1/cases/{id}
```

## Calls

``` text
GET  /api/v1/calls
POST /api/v1/calls
GET  /api/v1/calls/{id}
```

## Follow-ups

``` text
GET  /api/v1/followups
POST /api/v1/followups
GET  /api/v1/followups/{id}
PATCH /api/v1/followups/{id}
```

## Documents

``` text
GET  /api/v1/documents
POST /api/v1/documents/upload
GET  /api/v1/documents/{id}
DELETE /api/v1/documents/{id}
```

------------------------------------------------------------------------

# 17. Authorization

Do not rely only on Streamlit UI hiding buttons.

The FastAPI backend must enforce permissions.

Example:

``` text
ADMIN
  |
  +-- can view all customers
  +-- can view all cases
  +-- can manage users
  +-- can manage documents
  +-- can view reports
  +-- can view audit logs

CALL_CENTER
  |
  +-- can view assigned customers
  +-- can create/update cases
  +-- can view accessible calls
  +-- can schedule follow-ups
  +-- can use AI Assistant later
  +-- cannot manage users
  +-- cannot change system configuration
```

Authorization must happen before any future AI/RAG tool is allowed to
access customer information.

------------------------------------------------------------------------

# 18. Phase 1 Workflow

``` text
Agent Login
    |
    v
Agent Dashboard
    |
    v
Create Customer
    |
    v
Create Case
    |
    v
Record Human Call
    |
    v
Schedule Follow-up
    |
    v
Database
```

At this stage, the system is already useful without AI.

------------------------------------------------------------------------

# 19. Phase 2 — AI Integration ✅ Implemented

The AI engine is fully implemented in `backend/app/ai/` and installed
in `backend/ai_venv/`. The following components are live:

``` text
                    AI Agent (Groq LLM)
                       |
          +------------+------------+
          |            |            |
          v            v            v
        SQL           RAG          Tools
          |            |            |
          v            v            v
     PostgreSQL    FAISS Vector   Tavily
                   + Sentence     Web Search
                   Transformers
                        |
                   sentence-transformers
                   (all-MiniLM-L6-v2)
```

**AI venv location:** `backend/ai_venv/` ✅ installed

**AI requirements file:** `backend/ai_requirements.txt` ✅

**Key packages:**

| Package | Version | Role |
|---|---|---|
| `groq` | 1.6.0 | LLM inference |
| `sentence-transformers` | 5.7.0 | Text embeddings |
| `faiss-cpu` | 1.15.0 | Vector similarity search |
| `tavily-python` | 0.7.27 | Web search tool |
| `langchain-core` | 1.5.5 | Tool schemas |
| `pypdf` | 6.16.1 | PDF parsing for RAG |
| `torch` | 2.13.0 | Embedding model backend |

The Agent decides whether a question needs:

-   SQL/customer data
-   RAG/company knowledge
-   a web search tool
-   multiple sources

------------------------------------------------------------------------

# 20. Phase 3 --- Real Outbound Calls

Later add:

``` text
FastAPI
   |
   v
Follow-up Scheduler
   |
   v
Outbound Call Service
   |
   v
Telephony Provider
   |
   v
Real Customer Phone
   |
   v
YES / NO
   |
   +---- YES ---> RESOLVED
   |
   +---- NO ----> NEEDS_HUMAN
```

The outbound AI call should stay intentionally simple for this project:

``` text
Greeting
    |
Ask: "Was your problem resolved?"
    |
Speech Recognition
    |
YES / NO / UNKNOWN
    |
Update Case
    |
End Call
```

------------------------------------------------------------------------

# 21. Recommended Technology Stack

## Frontend

``` text
Streamlit
Python
Requests / HTTPX
```

## Backend

``` text
FastAPI
Pydantic
SQLAlchemy
Alembic
JWT Authentication
PostgreSQL
```

## Storage

``` text
Local storage for development
Object storage later if needed
```

## Future AI

``` text
LLM (Groq)                    ✅ implemented
Embeddings (sentence-transformers) ✅ implemented
Vector Database (FAISS)        ✅ implemented
Web Search (Tavily)            ✅ implemented
Agentic RAG                    ✅ implemented
Hybrid Search / Reranker       planned
```

## Future Telephony

``` text
Twilio Voice
STT
TTS
Webhook
```

------------------------------------------------------------------------

# 22. Repository Structure

Recommended GitHub repository:

``` text
nileconnect-ai-contact-center/
|
+-- frontend/
|
+-- backend/
|
+-- docs/
|   +-- architecture.md
|
+-- docker-compose.yml
+-- .env.example
+-- README.md
+-- .gitignore
```

For the first development phase, keep the repository simple:

``` text
frontend/
backend/
database/
docs/
```

Do not create separate microservices yet. A modular FastAPI backend is
enough for the demo.

------------------------------------------------------------------------

# 23. Final Architecture Decision

``` text
                NileConnect AI Contact Center
                         |
          +--------------+--------------+
          |                             |
     Streamlit                      FastAPI
     Frontend                       Backend
          |                             |
          |                     +-------+-------+
          |                     |               |
          |                 PostgreSQL     File Storage
          |                     |
          +---------------------+
                                |
                         Future AI Layer
                                |
                    +-----------+-----------+
                    |           |           |
                   SQL         RAG        Tools
                                |
                       Hybrid Retrieval
                                |
                           Reranker
                                |
                               LLM
                                |
                         Agentic RAG
                                |
                       Future AI Calling
                                |
                            Telephony
```

**Build order:**

1.  FastAPI project ✅
2.  PostgreSQL database ✅
3.  Authentication + RBAC ✅
4.  Customers ✅
5.  Cases ✅
6.  Calls ✅
7.  Follow-ups ✅
8.  Documents ✅
9.  Streamlit dashboards ✅
10. Connect Streamlit → FastAPI ✅
11. Test complete backend/frontend workflow ✅
12. AI layer — Groq LLM + FAISS + Tavily ✅ (Phase 2 complete)
13. Agentic RAG ✅ (Phase 2 complete)
14. Real outbound calling (Phase 3 — planned)
