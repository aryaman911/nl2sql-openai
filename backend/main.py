from __future__ import annotations
import os, re
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from openai_client import english_to_sql

load_dotenv()

app = FastAPI(title="English → SQL (Copy-Only)")

origins = os.getenv("CORS_ALLOW_ORIGINS")
allow = origins.split(",") if origins else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class NLRequest(BaseModel):
    question: str

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/nl2sql")
async def nl2sql(req: NLRequest):
    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Empty prompt")

    sql = english_to_sql(question)
    sql_one = re.sub(r"\s+", " ", sql).strip()

    if not re.match(r"(?i)^select\\b", sql_one):
        raise HTTPException(status_code=400, detail="Model must return a SELECT statement only")
    if ";" in sql_one.rstrip(";"):
        raise HTTPException(status_code=400, detail="Only a single statement is allowed")

    return {"sql": sql_one}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
