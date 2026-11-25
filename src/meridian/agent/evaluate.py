"""Evaluation harness for the AI Risk Analyst.

Execution accuracy: an answer is correct when the result the agent's last query
returned contains the gold answer (every value of the gold result, numbers
within 0.5% relative tolerance). This judges the data the agent retrieved, not
its wording, which is the standard way text-to-SQL systems are evaluated.

ScriptedClient is a deterministic test double, NOT a language model: it replays
the gold SQL and a templated answer so that the orchestration loop, guardrails
and scoring can be tested in CI without an API key.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

import duckdb
import pandas as pd

from meridian.agent.analyst import RiskAnalyst
from meridian.agent.guard import validate_sql

EVAL_PATH = Path(__file__).with_name("eval_set.json")


def load_eval_set() -> list[dict]:
    return json.loads(EVAL_PATH.read_text())


def _values(df: pd.DataFrame | None) -> list:
    if df is None or df.empty:
        return []
    return [v for v in df.head(10).to_numpy().ravel().tolist() if v is not None]


def _match(gold, got) -> bool:
    if isinstance(gold, (int, float)) and not isinstance(gold, bool):
        return any(isinstance(g, (int, float)) and not isinstance(g, bool) and not math.isnan(float(g))
                   and math.isclose(float(g), float(gold), rel_tol=5e-3, abs_tol=1e-9) for g in got)
    return str(gold).strip().lower() in {str(g).strip().lower() for g in got}


def is_correct(gold_df: pd.DataFrame, agent_df: pd.DataFrame | None) -> bool:
    got = _values(agent_df)
    return bool(got) and all(_match(v, got) for v in _values(gold_df))


@dataclass
class ScriptedClient:
    """Deterministic stand-in for an LLM: replays the gold SQL. For pipeline tests only."""
    gold_sql: str
    name: str = "Scripted test double (not an LLM)"
    _turn: int = 0

    def chat(self, system: str, messages: list[dict]) -> str:
        self._turn += 1
        if self._turn == 1:
            return json.dumps({"action": "sql", "query": self.gold_sql, "reason": "replay"})
        return json.dumps({"action": "answer", "text": "Answer based on the query result above.", "sources": ["gold"]})


def evaluate(con: duckdb.DuckDBPyConnection, make_analyst, items: list[dict] | None = None) -> pd.DataFrame:
    """Run every eval question through an analyst factory; return one row per question."""
    rows = []
    for item in items or load_eval_set():
        gold = con.execute(validate_sql(item["gold_sql"])).df()
        analyst: RiskAnalyst = make_analyst(item)
        try:
            res = analyst.ask(item["question"])
            ok, err = is_correct(gold, res.last_frame), ""
            steps, answer = len(res.steps), res.answer
        except Exception as exc:  # noqa: BLE001 - an evaluation must never crash on one item
            ok, err, steps, answer = False, f"{type(exc).__name__}: {exc}", 0, ""
        rows.append({"id": item["id"], "question": item["question"], "correct": ok, "steps": steps,
                     "answer": answer, "error": err})
    return pd.DataFrame(rows)
