"""Evaluate the AI Risk Analyst against a real LLM.

Usage:
    GEMINI_API_KEY=... python scripts/eval_agent.py
    GROQ_API_KEY=...   python scripts/eval_agent.py

Writes reports/agent_eval_live.csv and prints execution accuracy.
"""
from __future__ import annotations

import sys
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from meridian import config  # noqa: E402
from meridian.agent.analyst import RiskAnalyst  # noqa: E402
from meridian.agent.evaluate import evaluate  # noqa: E402
from meridian.agent.llm import client_from_env  # noqa: E402
from meridian.agent.retrieval import DocIndex, load_markdown  # noqa: E402


def main() -> None:
    llm = client_from_env()
    if llm is None:
        raise SystemExit("Set GEMINI_API_KEY or GROQ_API_KEY first.")
    con = duckdb.connect(str(config.APP_DB_PATH), read_only=True)
    docs = DocIndex(load_markdown([config.DOCS_DIR / "methodology.md", config.DOCS_DIR / "model_card_pd.md"]))
    res = evaluate(con, lambda item: RiskAnalyst(con, llm, docs))
    out = config.PROJECT_ROOT / "reports" / "agent_eval_live.csv"
    res.to_csv(out, index=False)
    print(res[["id", "correct", "steps", "error"]].to_string(index=False))
    print(f"\n{llm.name} ({getattr(llm, 'model', '')}): execution accuracy {res.correct.mean():.0%} "
          f"({res.correct.sum()}/{len(res)}). Saved {out.relative_to(config.PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
