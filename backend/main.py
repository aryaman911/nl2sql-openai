from __future__ import annotations
import os, re
from typing import Optional, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

import psycopg2
import psycopg2.extras

from openai_client import english_to_sql

load_dotenv()

app = FastAPI(title="English → SQL (Read-only)")

# ------------------------
# CORS
# ------------------------
origins = os.getenv("CORS_ALLOW_ORIGINS")
allow = [o for o in (origins.split(",") if origins else ["*"]) if o]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # demo: allow any origin
    allow_credentials=False,    # MUST be False when allow_origins=["*"]
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------
# Config
# ------------------------
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL not set — add your Supabase read-only connection string to env")

# ------------------------
# Models
# ------------------------
class NLRequest(BaseModel):
    question: str
    op: Optional[str] = None  # "auto" | "select" | "insert" | "update" | "delete"

class NLResponse(BaseModel):
    sql: str
    rows: List[dict]

# ------------------------
# DB helper (READ-ONLY)
# ------------------------
def run_select_query(sql: str) -> List[dict]:
    """
    Execute a SELECT query on the Supabase Postgres database
    using a read-only user. Returns a list of dict rows.
    """
    # Supabase usually requires SSL
    with psycopg2.connect(DATABASE_URL, sslmode="require") as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql)
            rows = cur.fetchall()
            return [dict(r) for r in rows]

# ------------------------
# Safety / validation
# ------------------------
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

    # Guardrail 1: single statement only
    if ";" in sql_one.rstrip(";"):
        raise HTTPException(
            status_code=400,
            detail="Only a single SQL statement is allowed"
        )

    # Guardrail 2: must start with SELECT
    if not re.match(r"(?i)^\s*select\b", sql_one):
        raise HTTPException(
            status_code=400,
            detail="This deployment is read-only — only SELECT statements are allowed"
        )

    # Guardrail 3: block any write/DDL verbs just in case
    if FORBIDDEN_KEYWORDS.search(sql_one):
        raise HTTPException(
            status_code=400,
            detail="Write/DDL operations are disabled — database is read-only"
        )

    return sql_one

# ------------------------
# Routes
# ------------------------
@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/nl2sql", response_model=NLResponse)
async def nl2sql(req: NLRequest):
    q = (req.question or "").strip()
    if not q:
        raise HTTPException(status_code=400, detail="Empty prompt")

    # If client asks for non-select ops, reject (we want read-only)
    if req.op and req.op.lower() not in ("auto", "select"):
        raise HTTPException(
            status_code=400,
            detail="This deployment is read-only — only SELECT operations are supported"
        )

    # 1) Use the model to generate SQL
    #    Hard-force "select" behaviour so english_to_sql doesn't try writes.
    sql = english_to_sql(q, "select")

    # 2) Validate & sanitize for read-only safety
    safe_sql = validate_readonly_sql(sql)

    # 3) Execute on Supabase read-only DB
    try:
        rows = run_select_query(safe_sql)
    except psycopg2.Error as e:
        # Return a clean error to frontend, with minimal DB leakage
        msg = e.pgerror or str(e)
        raise HTTPException(
            status_code=400,
            detail=f"Database error while executing SQL: {msg}"
        )

    # 4) Return both SQL and data to frontend
    return NLResponse(sql=safe_sql, rows=rows)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
