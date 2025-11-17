from __future__ import annotations

import os
from typing import Optional

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# Use OpenAI's Python SDK v1.x style client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# You can override the model via env if you want (e.g., gpt-4o)
MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

SYSTEM_PROMPT = """
You are an expert SQL generator.

You MUST follow these rules:

1. Only generate SQL using the tables and columns listed below.
2. Do NOT invent tables, columns, or relationships.
3. Always output ONE SINGLE SQL SELECT statement and nothing else.
4. No explanations, no markdown — ONLY SQL.
5. Always prefer readable column aliases.
6. Always include a WHERE clause unless the user explicitly asks for all rows.
7. You are working with a static medical database — you MUST NOT generate INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, or CREATE.

----------------------------
AVAILABLE TABLES & COLUMNS
----------------------------

TABLE: Patient
- patient_id
- first_name
- last_name
- age
- gender
- address

TABLE: Medication
- medication_id
- name
- dosage
- manufacturer

TABLE: Patient_Medication
- patient_id       (FK → Patient.patient_id)
- medication_id    (FK → Medication.medication_id)
- start_date
- end_date
- dosage_instructions

TABLE: Patient_History
- patient_id       (FK → Patient.patient_id)
- diagnosis
- visit_date
- doctor_name
- notes

----------------------------
Your ONLY job:
Given a natural language question, return ONE SQL SELECT query that only uses the schema above.
"""


def english_to_sql(question: str, op: Optional[str] = None) -> str:
    """
    Convert an English question into a single SQL SELECT statement
    constrained to the schema defined in SYSTEM_PROMPT.
    """
    question = (question or "").strip()
    if not question:
        return ""

    # Optionally include the desired op for clarity, even though we force SELECT in backend
    if op and op.lower() in ("select", "insert", "update", "delete"):
        user_content = f"Operation: {op.upper()}\n\nQuestion: {question}"
    else:
        user_content = question

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        temperature=0,
    )

    sql = response.choices[0].message.content or ""
    sql = sql.strip()

    # Just return as-is; main.py will normalize whitespace and guardrail.
    return sql
