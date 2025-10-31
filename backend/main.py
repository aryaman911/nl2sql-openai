from __future__ import annotations
import os, re
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from openai_client import english_to_sql


load_dotenv()

app = FastAPI(title="English → SQL")

# CORS
origins = os.getenv("CORS_ALLOW_ORIGINS")
allow = [o for o in (origins.split(",") if origins else ["*"]) if o]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # demo: allow any origin
    allow_credentials=False,    # MUST be False when allow_origins=["*"]
    allow_methods=["*"],
    allow_headers=["*"],
)
ALLOW_DDL = os.getenv("ALLOW_DDL", "false").lower() in ("1", "true", "yes")

class NLRequest(BaseModel):
    question: str
    op: Optional[str] = None  # "auto" | "select" | "insert" | "update" | "delete"

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/nl2sql")
async def nl2sql(req: NLRequest):
    q = (req.question or "").strip()
    if not q:
        raise HTTPException(status_code=400, detail="Empty prompt")

    # Generate
    sql = english_to_sql(q, req.op)
    # One line + trim
    sql_one = re.sub(r"\s+", " ", sql).strip()

    # Guardrail 1: single statement only (no chains like '...; DROP ...')
    if ";" in sql_one.rstrip(";"):
        raise HTTPException(status_code=400, detail="Only a single SQL statement is allowed")

    # Guardrail 2: optionally block dangerous DDL
    if not ALLOW_DDL:
        danger = re.compile(r"(?i)\b(DROP|TRUNCATE|ALTER)\b")
        if danger.search(sql_one):
            raise HTTPException(status_code=400, detail="Dangerous DDL disabled in this demo")

    # Guardrail 3: if op specified, enforce starting verb
    if req.op and req.op.lower() != "auto":
        verb = req.op.lower()
        starts = {
            "select": r"(?i)^\s*select\b",
            "insert": r"(?i)^\s*insert\b",
            "update": r"(?i)^\s*update\b",
            "delete": r"(?i)^\s*delete\b",
        }[verb]
        if not re.match(starts, sql_one):
            raise HTTPException(status_code=400, detail=f"Expected a {verb.upper()} statement")

        # Extra safety for update/delete: must contain WHERE
        if verb in {"update", "delete"} and not re.search(r"(?i)\bwhere\b", sql_one):
            raise HTTPException(status_code=400, detail=f"{verb.upper()} must include a WHERE clause")

    return {"sql": sql_one}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
