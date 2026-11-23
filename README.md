# 📊 AI Data Analyst Agent

Ask a database questions in **Arabic or English**. The agent writes the SQL, **validates and runs it safely**, **fixes its own mistakes**, and explains the result in plain language, with the SQL, the data table and a chart one click away.

> "ما هي أعلى 5 منتجات من حيث الإيرادات؟" → SQL → table → *"المنتج الأعلى إيرادًا هو …"*

## Why this project

Letting an LLM write SQL is easy. Letting it do so **safely and reliably** is the real engineering problem. This project focuses on exactly that:

| Concern | How it's handled |
|---|---|
| **Safety** | 3 independent layers: (1) a SQL validator that allows only a single `SELECT` / `WITH … SELECT` and blocks `DROP`, `DELETE`, `PRAGMA`, `ATTACH`, multi-statements, …; (2) a **read-only SQLite connection** (`mode=ro`), so even a validator bypass can't write; (3) a **time limit** and **row cap** on every query. |
| **Reliability** | An agent loop: when the query is rejected or fails (unknown column, syntax error…), the error is sent back to the model to **self-correct**, up to N retries. |
| **Honesty** | Out-of-scope questions ("what's the weather?") get a clear *"can't be answered from this database"* instead of a made-up query. |
| **Measurability** | An **execution-accuracy** evaluation: the agent's result set is compared to a gold query's result set on a bilingual question set. |
| **Grounded explanations** | The final answer is generated only from the returned rows. |

## Architecture

```
question (AR/EN)
   │
   ▼
 LLM ──► SQL ──► validator ──► read-only DB (timeout, row cap) ──► rows ──► LLM ──► answer
   ▲                │ rejected                 │ error
   └────────────────┴──────── feedback loop ◄──┘   (self-correction, max retries)
```

| Module | Responsibility |
|---|---|
| `guard.py` | SQL validator (layer 1) |
| `db.py` | read-only connection, timeout, row cap, schema + sample rows for the prompt |
| `agent.py` | the agent loop: generate → validate → execute → self-correct → explain |
| `prompts.py` | SQL-generation and summary prompts (schema-aware, bilingual) |
| `sample_data.py` | seeded synthetic e-commerce database (customers, products, orders, order_items) |
| `api.py` / `app.py` | FastAPI service / Streamlit UI (with auto-chart) |

## Quick start

```bash
git clone https://github.com/rihamibrahim17/ai-data-analyst-agent.git
cd ai-data-analyst-agent
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                   # add GOOGLE_API_KEY (free: https://aistudio.google.com/apikey)

export PYTHONPATH=src                                  # Windows PowerShell: $env:PYTHONPATH="src"
python -m data_analyst.sample_data                     # creates data/shop.db
streamlit run app.py                                   # UI
# or the REST API:
uvicorn data_analyst.api:app --reload
```

Switch to OpenAI with `LLM_PROVIDER=openai` and `OPENAI_API_KEY` in `.env`.

### API example

```bash
curl -X POST http://localhost:8000/ask -H "Content-Type: application/json" \
  -d '{"question": "How many delivered orders per city?"}'
```

### Use your own database
Point `DB_PATH` at any SQLite file. The schema (including `-- comments` on columns) and a few sample rows are injected into the prompt automatically; put business rules in `BUSINESS_NOTES`.

## Tests & evaluation

```bash
pip install -r requirements-dev.txt
pytest -q     # 35 tests, no API key needed (fake LLM, real SQLite)
```

The tests cover the SQL validator (safe and malicious inputs), read-only enforcement, query timeouts, row caps, the self-correction loop, out-of-scope handling and the API.

```bash
python eval/run_eval.py    # needs an API key
```
reports **execution accuracy** (result set equals the gold query's result set), plus how many answers were fixed by self-correction.

## Roadmap

- Conversation memory for follow-ups ("and by month?")
- PostgreSQL / MySQL support with a read-only role
- Query result caching and few-shot examples retrieved per question
- Tool-calling with a chart tool, and streaming responses

## Tech stack

Python · LangChain · Google Gemini / OpenAI · SQLite · FastAPI · Streamlit · pandas · Docker · pytest · GitHub Actions
