# backend/openai_client.py
from __future__ import annotations
import os
from typing import Optional
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI()  # reads OPENAI_API_KEY from env
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")

SYSTEM_PROMPT = (
    "You are an expert SQL developer. Convert user requests into a single SQL statement.\n"
    "Output ONLY the SQL, with no explanations or markdown.\n"
    "If a target operation is provided, the statement MUST start with that verb.\n"
    "INSERT: include explicit column list; prefer placeholders (:id, :name).\n"
    "UPDATE/DELETE: ALWAYS include a restrictive WHERE clause.\n"
    "SELECT: prefer explicit columns and LIMIT when appropriate.\n"
)

def english_to_sql(question: str, op: Optional[str] = None) -> str:
    question = (question or "").strip()
    target = f"Target operation: {op.upper()}" if op and op.lower() != "auto" else "Target operation: AUTO"

    # Use Chat Completions for broad compatibility across SDK versions
    resp = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"{target}\nNatural language request: {question}\nSQL:"},
        ],
        temperature=0,
        max_tokens=400,
    )
    return (resp.choices[0].message.content or "").strip()
