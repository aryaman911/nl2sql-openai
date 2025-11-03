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
You are an expert SQL developer working with a healthcare database.
Only use the following tables and columns when generating SQL:

TABLE: Patient
- patient_id (primary key)
- first_name
- last_name
- age
- gender
- address

TABLE: Medication
- medication_id (primary key)
- name
- dosage
- manufacturer

TABLE: Patient_Medication
- patient_id (foreign key references Patient)
- medication_id (foreign key references Medication)
- start_date
- end_date
- dosage_instructions

TABLE: Patient_History
- patient_id (foreign key references Patient)
- diagnosis
- visit_date
- doctor_name
- notes

Rules:
1. Generate **only one SQL statement** per query.
2. Use proper JOINs based on foreign key relationships.
3. Prefer readable column aliases.
4. Do not invent tables or columns outside these.
5. Do not include explanations or markdown — output raw SQL only.
6. Always include WHERE clauses for UPDATE and DELETE queries.
7. When asked for patient-medication data, join Patient, Medication, and Patient_Medication appropriately.
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
