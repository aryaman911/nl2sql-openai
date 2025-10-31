import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")

SYSTEM_PROMPT = (
    "You are an expert SQL developer. Convert user questions into precise SQL queries.\n"
    "Only output the SQL statement — no explanations, comments, or markdown.\n"
    "Always produce a single SELECT statement (no DDL/DML)."
)

def english_to_sql(question: str) -> str:
    question = question.strip()
    resp = client.responses.create(
        model=MODEL_NAME,
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f'Natural language request: {question}\\nSQL Query:'},
        ],
        max_output_tokens=400,
    )
    return resp.output[0].content[0].text.strip()
