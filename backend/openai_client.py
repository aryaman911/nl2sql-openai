from __future__ import annotations
import os
from typing import Optional
from dotenv import load_dotenv
from openai import OpenAI
client = OpenAI()  # ← use env OPENAI_API_KEY

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")

SYSTEM_PROMPT = (
    "You are an expert SQL developer. Convert user requests into a single SQL statement.\n"
    "Output ONLY the SQL, no explanations, comments, or markdown.\n"
    "If a target operation is provided, the statement MUST start with that verb.\n"
    "When generating DML:\n"
    " - INSERT: always include explicit column list and VALUES; prefer placeholders (e.g., :name, :id).\n"
    " - UPDATE/DELETE: ALWAYS include a restrictive WHERE clause.\n"
    " - SELECT: prefer explicit columns and LIMIT when user implies small results.\n"
)

def english_to_sql(question: str, op: Optional[str] = None) -> str:
    """
    Generate a single SQL statement. If op in {select, insert, update, delete}, bias to that verb.
    """
    question = question.strip()
    target = f"Target operation: {op.upper()}" if op and op.lower() != "auto" else "Target operation: AUTO"
    resp = client.responses.create(
        model=MODEL_NAME,
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"{target}\nNatural language request: {question}\nSQL:"},
        ],
        max_output_tokens=500,
    )
    return resp.output[0].content[0].text.strip()
