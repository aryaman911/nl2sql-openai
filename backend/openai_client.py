# backend/openai_client.py
from __future__ import annotations
import os
from typing import Optional
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI()  # reads OPENAI_API_KEY from env
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")

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
- patient_id   (FK → Patient.patient_id)
- medication_id (FK → Medication.medication_id)
- start_date
- end_date
- dosage_instructions

TABLE: Patient_History
- patient_id   (FK → Patient.patient_id)
- diagnosis
- visit_date
- doctor_name
- notes

----------------------------
Your ONLY job:
Given a natural language question, return ONE SQL SELECT query that only uses the schema above.
"""

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
