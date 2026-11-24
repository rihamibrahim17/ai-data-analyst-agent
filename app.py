"""Streamlit UI.  Run:  streamlit run app.py"""
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent / "src"))

from data_analyst.config import Settings  # noqa: E402
from data_analyst.factory import get_agent  # noqa: E402
from data_analyst.sample_data import create_sample_db  # noqa: E402

st.set_page_config(page_title="AI Data Analyst", page_icon="📊", layout="wide")
st.markdown("<style>.stMarkdown p {unicode-bidi: plaintext; text-align: start;}</style>", unsafe_allow_html=True)


@st.cache_resource
def load_agent():
    db_path = Settings.from_env().db_path
    if not db_path.exists():  # fresh server (e.g. cloud demo): create the sample database
        create_sample_db(db_path)
    return get_agent()


st.title("📊 AI Data Analyst Agent")
st.caption("Ask the shop database a question in Arabic or English. The agent writes the SQL, runs it safely, and explains the result.")

examples = [
    "How many delivered orders do we have per city?",
    "ما هي أعلى 5 منتجات من حيث الإيرادات؟",
    "What was the monthly revenue in 2026?",
    "كم عدد العملاء في القاهرة؟",
]
with st.sidebar:
    st.header("Try an example")
    for ex in examples:
        if st.button(ex):
            st.session_state["question"] = ex

question = st.text_input("Your question", key="question", placeholder="e.g. Which category sells the most?")

if question:
    with st.spinner("Analysing…"):
        try:
            result = load_agent().ask(question)
        except Exception as exc:
            st.error(f"Something went wrong: {exc}")
            st.stop()

    (st.success if result.ok else st.warning)(result.answer)

    if result.sql:
        with st.expander("Generated SQL", expanded=False):
            st.code(result.sql, language="sql")
        df = pd.DataFrame(result.rows, columns=result.columns)
        st.dataframe(df)
        if result.truncated:
            st.caption("Showing the first rows only (result truncated).")
        # Auto-chart: one text/label column + one numeric column
        if len(df.columns) == 2 and pd.api.types.is_numeric_dtype(df.iloc[:, 1]) and len(df) > 1:
            st.bar_chart(df.set_index(df.columns[0]))

    failed = [a for a in result.attempts if a.error]
    if failed:
        with st.expander(f"Self-corrections ({len(failed)})"):
            for a in failed:
                st.code(a.sql or "(no SQL)", language="sql")
                st.caption(f"Rejected: {a.error}")
