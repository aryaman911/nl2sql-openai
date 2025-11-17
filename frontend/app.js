const BACKEND = (window.BACKEND_URL || "http://localhost:8000").replace(/\/$/, "");
document.getElementById("backend-url").textContent = BACKEND;

const form = document.getElementById("qform");
const questionEl = document.getElementById("question");
const opEl = document.getElementById("op");
const resultEl = document.getElementById("result");
const sqlEl = document.getElementById("sql");
const rowsEl = document.getElementById("rows");
const copyBtn = document.getElementById("copy");

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const question = questionEl.value.trim();
  const op = opEl.value;
  if (!question) return;

  sqlEl.textContent = "Generating SQL and running query...";
  rowsEl.textContent = "";
  resultEl.classList.remove("hidden");

  try {
    const r = await fetch(`${BACKEND}/nl2sql`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, op }),
    });

    if (!r.ok) {
      // Try to extract error message from backend
      let msg = await r.text();
      try {
        const parsed = JSON.parse(msg);
        msg = parsed.detail || msg;
      } catch {
        // leave msg as-is
      }
      throw new Error(msg);
    }

    const data = await r.json();
    sqlEl.textContent = data.sql || "(no SQL returned)";

    if (Array.isArray(data.rows)) {
      rowsEl.textContent =
        data.rows.length > 0
          ? JSON.stringify(data.rows, null, 2)
          : "(no rows returned)";
    } else {
      rowsEl.textContent = "(no rows returned)";
    }
  } catch (err) {
    sqlEl.textContent = "Error";
    rowsEl.textContent = `Error: ${err.message || err}`;
  }
});

copyBtn.addEventListener("click", async () => {
  const text = sqlEl.textContent.trim();
  if (!text) return;
  try {
    await navigator.clipboard.writeText(text);
    copyBtn.textContent = "Copied!";
    setTimeout(() => (copyBtn.textContent = "Copy"), 1200);
  } catch {
    // ignore clipboard errors
  }
});
