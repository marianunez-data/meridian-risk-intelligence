import streamlit as st
from lib import ui
from lib.data import DOCS, connection

from meridian.agent.analyst import RiskAnalyst
from meridian.agent.guard import GuardError, validate_sql
from meridian.agent.llm import client_from_env
from meridian.agent.retrieval import DocIndex, load_markdown

ui.header("AI", "AI Risk Analyst",
          "Ask a question about the loan book, stress test, fraud or suppliers in plain English. The analyst writes SQL "
          "against a governed, read-only warehouse and searches the methodology, then answers with its sources.")


@st.cache_resource(show_spinner=False)
def doc_index() -> DocIndex:
    return DocIndex(load_markdown([DOCS / "methodology.md", DOCS / "model_card_pd.md"]))


try:
    secrets = dict(st.secrets)
except Exception:  # noqa: BLE001 - no secrets file locally
    secrets = {}
llm = client_from_env(secrets)
con = connection()

EXAMPLES = [
    "What is the 24-month bad rate by grade for loans issued in 2016?",
    "How much would the live book lose in the severely adverse scenario?",
    "Which sector has the highest share of suppliers in the distress zone?",
    "Why did tax liens drift in 2018?",
    "How much fraud value did the rule engine miss in the test period?",
]

if llm is None:
    st.info("The analyst needs a free API key from Google AI Studio (GEMINI_API_KEY) or Groq (GROQ_API_KEY), added to the "
            "app's secrets. Until then, the governed SQL console below shows the same guardrails the analyst runs under.")
else:
    st.caption(f"Model provider: {llm.name}. Answers come only from governed tables and project documentation.")
    if "chat" not in st.session_state:
        st.session_state.chat = []
    cols = st.columns(len(EXAMPLES))
    clicked = None
    for c, ex in zip(cols, EXAMPLES):
        if c.button(ex, width="stretch"):
            clicked = ex
    for turn in st.session_state.chat:
        with st.chat_message(turn["role"]):
            st.markdown(turn["content"])
            if turn.get("sql"):
                with st.expander("SQL and data"):
                    st.code(turn["sql"], language="sql")
                    st.dataframe(turn["frame"], hide_index=True, width="stretch")
    question = st.chat_input("Ask about the loan book, stress test, fraud or suppliers") or clicked
    if question:
        st.session_state.chat.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)
        with st.chat_message("assistant"):
            with st.spinner("Querying the warehouse"):
                try:
                    res = RiskAnalyst(con.cursor(), llm, doc_index()).ask(question)
                    answer = res.answer + (f"\n\n<span style='color:{ui.MUTED};font-size:0.8rem'>Sources: "
                                           f"{', '.join(res.sources)}</span>" if res.sources else "")
                except Exception as err:  # noqa: BLE001
                    status = getattr(getattr(err, "response", None), "status_code", None)
                    hint = {400: "the API key or request was rejected", 401: "the API key is invalid",
                            403: "the API key has no access to this model", 404: "the model name is not available to this key",
                            429: "the free-tier quota is used up; try again later",
                            503: "the model is temporarily overloaded; try again in a minute"}.get(status, "")
                    detail = f"{type(err).__name__} {status}" if status else type(err).__name__
                    res, answer = None, (f"The analyst could not complete this request ({detail}"
                                         f"{': ' + hint if hint else ''}). Please try again.")
            st.markdown(answer, unsafe_allow_html=True)
            turn = {"role": "assistant", "content": answer}
            if res is not None and res.last_sql:
                with st.expander("SQL and data"):
                    st.code(res.last_sql, language="sql")
                    st.dataframe(res.last_frame, hide_index=True, width="stretch")
                turn.update(sql=res.last_sql, frame=res.last_frame)
            st.session_state.chat.append(turn)

st.header("Governed SQL console")
st.caption("Read-only access to the same 16 governed tables. Try a destructive query to see the guardrail respond.")
default_sql = ("select grade, sum(bad_24m) / sum(loans_with_24m_outcome) as bad_rate_24m\n"
               "from portfolio_cube\nwhere year(issue_month) = 2016\ngroup by grade\norder by grade")
sql = st.text_area("SQL", default_sql, height=140, label_visibility="collapsed")
if st.button("Run query", type="primary"):
    try:
        safe = validate_sql(sql)
        st.code(safe, language="sql")
        st.dataframe(con.cursor().execute(safe).df(), hide_index=True, width="stretch")
    except GuardError as err:
        st.error(f"Blocked by guardrail: {err}")
    except Exception as err:  # noqa: BLE001
        st.error(f"Query error: {str(err).splitlines()[0]}")

with st.expander("How the analyst stays safe"):
    st.markdown("""
- The language model never runs SQL itself. It proposes a query; a parser-based guard checks it.
- Only one read-only statement is allowed, only on 16 governed tables, with no file access or table functions, and at most 500 rows.
- The database connection is opened read-only, so even an unforeseen query cannot change data.
- Answers must come from tool results; the prompt forbids invented numbers. A 16-question evaluation set measures execution accuracy.
""")
ui.footer()
