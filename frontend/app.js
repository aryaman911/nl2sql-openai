const BACKEND = (window.BACKEND_URL || "http://localhost:8000").replace(/\/$/, "");
document.getElementById("backend-url").textContent = BACKEND;

const form = document.getElementById("qform");
const questionEl = document.getElementById("question");
const resultEl = document.getElementById("result");
const sqlEl = document.getElementById("sql");
const copyBtn = document.getElementById("copy");

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const question = questionEl.value.trim();
  if (!question) return;
  sqlEl.textContent = "Generating...";
  resultEl.classList.remove("hidden");

  try {
    const r = await fetch(`${BACKEND}/nl2sql`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    if (!r.ok) throw new Error(await r.text());
    const data = await r.json();
    sqlEl.textContent = data.sql || "(no SQL returned)";
  } catch (err) {
    sqlEl.textContent = `Error: ${err.message || err}`;
  }
});

copyBtn.addEventListener("click", async () => {
  const text = sqlEl.textContent.trim();
  if (!text) return;
  try {
    await navigator.clipboard.writeText(text);
    copyBtn.textContent = "Copied!";
    setTimeout(() => (copyBtn.textContent = "Copy"), 1200);
  } catch {}
});
