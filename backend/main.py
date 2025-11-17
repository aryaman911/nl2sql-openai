from __future__ import annotations

import os
import re
from typing import Optional, List
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

import pg8000

from openai_client import english_to_sql

# --------------------------------------------------
# Load env
# --------------------------------------------------
load_dotenv()

app = FastAPI(title="English → SQL (Read-only)")

# --------------------------------------------------
# CORS
# --------------------------------------------------
origins = os.getenv("CORS_ALLOW_ORIGINS")
allow = [o for o in (origins.split(",") if origins else ["*"]) if o]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow or ["*"],
    allow_credentials=False,  # MUST be False when allow_origins=["*"]
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------------------------
# Database config
# --------------------------------------------------
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL not set — add your Supabase connection string to env")

# Example: postgresql://postgres:password@db.xxxxx.supabase.co:5432/postgres?sslmode=require
parsed = urlparse(DATABASE_URL)

DB_KWARGS = {
    "user": parsed.username,
    "password": parsed.password,
    "host": parsed.hostname,
    "port": parsed.port or 5432,
    "database": parsed.path.lstrip("/") or "postgres",
    # Supabase requires SSL; True = create default SSL context in pg8000
    "ssl_context": True,
}

# --------------------------------------------------
# Pydantic models
# --------------------------------------------------
class NLRequest(BaseModel):
    question: str
    op: Optional[str] = None  # "auto" | "select" | (writes are rejected)


class NLResponse(BaseModel):
    sql: str
    rows: List[dict]


# --------------------------------------------------
# DB helper (READ-ONLY)
# --------------------------------------------------
def run_select_query(sql: str) -> List[dict]:
    """
    Execute a SELECT query on the Supabase Postgres database
    using a read-only user. Returns a list of dict rows.
    """
    with pg8000.connect(**DB_KWARGS) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            # Column names from cursor.description
            columns = [desc[0] for desc in cur.description]
            data = cur.fetchall()
            return [dict(zip(columns, row)) for row in data]


# --------------------------------------------------
# Safety / validation
# --------------------------------------------------
FORBIDDEN_KEYWORDS = re.compile(
    r"(?i)\b(INSERT|UPDATE|DELETE|DROP|TRUNCATE|ALTER|CREATE|REPLACE)\b"
)


def validate_readonly_sql(sql: str) -> str:
    """
    Enforce:
    - Single statement
    - SELECT only
    - No DDL / DML
    """
    sql_one = re.sub(r"\s+", " ", sql).strip()

    # Guardrail 1: single statement only (no '...; DROP ...')
    if ";" in sql_one.rstrip(";"):
        raise HTTPException(
            status_code=400,
            detail="Only a single SQL statement is allowed",
        )

    # Guardrail 2: must start with SELECT
    if not re.match(r"(?i)^\s*select\b", sql_one):
        raise HTTPException(
            status_code=400,
            detail="This deployment is read-only — only SELECT statements are allowed",
        )

    # Guardrail 3: block any write/DDL verbs just in case
    if FORBIDDEN_KEYWORDS.search(sql_one):
        raise HTTPException(
            status_code=400,
            detail="Write/DDL operations are disabled — database is read-only",
        )

    return sql_one


# --------------------------------------------------
# Routes
# --------------------------------------------------
@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/nl2sql", response_model=NLResponse)
async def nl2sql(req: NLRequest):
    # Basic input check
    q = (req.question or "").strip()
    if not q:
        raise HTTPException(status_code=400, detail="Empty prompt")

    # If client tries to request non-select op, reject up front
    if req.op and req.op.lower() not in ("auto", "select"):
        raise HTTPException(
            status_code=400,
            detail="This deployment is read-only — only SELECT operations are supported",
        )

    # 1) Use the model to generate SQL, forcing SELECT behaviour
    sql = english_to_sql(q, "select")

    # 2) Validate & sanitize for read-only safety
    safe_sql = validate_readonly_sql(sql)

    # 3) Execute on Supabase read-only DB
    try:
        rows = run_select_query(safe_sql)
    except Exception as e:
        # Return a clean error to frontend, with minimal DB leakage
        msg = str(e)
        raise HTTPException(
            status_code=400,
            detail=f"Database error while executing SQL: {msg}",
        )

    # 4) Return both SQL and data to frontend
    return NLResponse(sql=safe_sql, rows=rows)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
