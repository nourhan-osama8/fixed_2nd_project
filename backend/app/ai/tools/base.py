"""
Agent tools — three LangChain-compatible @tool functions:

1. database_query   — READ-ONLY PostgreSQL queries (SELECT / WITH only)
2. rag_search_tool  — FAISS semantic search over uploaded company documents
3. web_search_tool  — Tavily public web search

SQL safety:
  • Only SELECT and WITH statements are allowed.
  • A whitelist of forbidden SQL keywords (INSERT, UPDATE, DELETE, DROP, …)
    is checked with word-boundary regex before any query is executed.
  • The PostgreSQL connection is opened in a context-manager that auto-closes.
  • No DDL is possible because the DB user only needs read access, and the
    code-level guard provides a second layer of defence.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Tuple

import psycopg2
from langchain_core.tools import tool
from tavily import TavilyClient

from app.core.config import settings
from app.ai.rag.pipeline import rag

logger = logging.getLogger("nileconnect")

# ── SQL Safety ────────────────────────────────────────────────────────────────

_FORBIDDEN_SQL = [
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE",
    "REPLACE", "ATTACH", "DETACH", "VACUUM", "TRUNCATE",
    "GRANT", "REVOKE", "CALL", "EXEC", "EXECUTE",
]


def _validate_sql(sql: str) -> Tuple[bool, str | None]:
    """
    Return (True, None) if *sql* is a safe read-only query,
    or (False, reason) if it contains forbidden operations.
    """
    clean = sql.strip().upper()

    if not (clean.startswith("SELECT") or clean.startswith("WITH")):
        return False, "Only SELECT or WITH queries are allowed."

    for keyword in _FORBIDDEN_SQL:
        if re.search(rf"\b{keyword}\b", clean):
            return False, f"Forbidden SQL operation detected: {keyword}"

    return True, None


# ── Tool 1: Database Query ────────────────────────────────────────────────────

@tool
def database_query(sql: str) -> str:
    """
    Execute a READ-ONLY SQL query against the NileConnect PostgreSQL database.

    ALLOWED: SELECT, WITH (CTEs).
    FORBIDDEN: INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE, etc.

    Always search by name/phone first to find the customer ID before
    querying related tables. Never hard-code IDs.

    Example queries:
        SELECT * FROM customers WHERE name ILIKE '%Ahmed%'
        SELECT * FROM cases WHERE customer_id = '<uuid>'
        SELECT * FROM calls WHERE customer_id = '<uuid>' ORDER BY started_at DESC
    """
    valid, error = _validate_sql(sql)
    if not valid:
        logger.warning("AI agent blocked SQL: %s — reason: %s", sql[:200], error)
        return json.dumps({"success": False, "error": error})

    try:
        conn = psycopg2.connect(settings.DATABASE_URL)
        conn.set_session(readonly=True, autocommit=True)
        with conn.cursor() as cur:
            cur.execute(sql)
            columns = [desc[0] for desc in cur.description] if cur.description else []
            rows = cur.fetchall()
        conn.close()

        result = [dict(zip(columns, row)) for row in rows]
        # Serialize UUIDs and dates as strings
        result_serializable = json.loads(
            json.dumps(result, default=str)
        )
        return json.dumps({"success": True, "row_count": len(result_serializable), "rows": result_serializable}, ensure_ascii=False)

    except Exception as exc:
        logger.error("database_query error: %s", exc)
        return json.dumps({"success": False, "error": str(exc)})


# ── Tool 2: RAG Search ────────────────────────────────────────────────────────

@tool
def rag_search_tool(question: str) -> str:
    """
    Search internal company documents, PDFs, policies, manuals, and SOPs
    that have been uploaded to the NileConnect knowledge base.

    Use this for:
    - Company internal policies (refund, escalation, SLA)
    - Product/service documentation
    - Troubleshooting guides
    - Any question about company procedures or rules

    Do NOT use this for real-time customer data (use database_query instead).
    """
    results = rag.search(question, k=4)

    if not results:
        return json.dumps({"success": False, "message": "No relevant documents found in the knowledge base."})

    return json.dumps({"success": True, "results": results}, ensure_ascii=False)


# ── Tool 3: Web Search ────────────────────────────────────────────────────────

def _make_tavily() -> TavilyClient | None:
    if not settings.TAVILY_API_KEY:
        return None
    return TavilyClient(api_key=settings.TAVILY_API_KEY)


_tavily_client: TavilyClient | None = _make_tavily()


@tool
def web_search_tool(query: str) -> str:
    """
    Search the public web using Tavily.

    Use this for:
    - Current events and recent news
    - Latest software/firmware versions
    - Public information not available in internal documents
    - General knowledge questions

    Do NOT use this for internal company data or customer records.
    """
    if _tavily_client is None:
        return json.dumps({"success": False, "error": "Tavily API key not configured."})

    try:
        response = _tavily_client.search(
            query=query,
            search_depth="basic",
            max_results=5,
        )
        results = [
            {"title": item.get("title"), "url": item.get("url"), "content": item.get("content")}
            for item in response.get("results", [])
        ]
        return json.dumps({"success": True, "results": results}, ensure_ascii=False)

    except Exception as exc:
        logger.error("web_search_tool error: %s", exc)
        return json.dumps({"success": False, "error": str(exc)})


# ── Tool registry ─────────────────────────────────────────────────────────────

TOOLS = [database_query, rag_search_tool, web_search_tool]

TOOL_MAP = {t.name: t for t in TOOLS}


def get_tool_schemas() -> list:
    """Return OpenAI-compatible tool schemas for all tools."""
    return [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description,
                "parameters": t.args_schema.model_json_schema(),
            },
        }
        for t in TOOLS
    ]
