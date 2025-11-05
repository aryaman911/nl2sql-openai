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

TABLE: PATIENT
- patient_id (primary key)
- first_name
- last_name
- age
- gender
- address

TABLE: M_MEDICATION
- medication_id (primary key)
- name
- dosage
- manufacturer

TABLE: PATIENT_MEDICATION
- patient_id (foreign key references PATIENT)
- medication_id (foreign key references M_MEDICATION)
- start_date
- end_date
- dosage_instructions

TABLE: M_ICD
- icd_id (primary key)
- code
- description

TABLE: PATIENT_ICD
- patient_id (foreign key references PATIENT)
- icd_id (foreign key references M_ICD)
- diagnosis_date
- doctor_name
- notes

Rules:
1. Generate **only one SQL statement** per query.
2. Use proper JOINs based on foreign key relationships.
3. Prefer readable column aliases.
4. Do not invent tables or columns outside these.
5. Do not include explanations or markdown — output raw SQL only.
6. Always include WHERE clauses for UPDATE and DELETE queries.
7. When asked for patient-medication data, join PATIENT, M_MEDICATION, and PATIENT_MEDICATION appropriately.
8. When asked for patient diagnosis or ICD data, join PATIENT, M_ICD, and PATIENT_ICD appropriately.
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
