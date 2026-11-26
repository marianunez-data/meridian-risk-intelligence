"""The AI Risk Analyst: a small tool-using agent loop.

The model never sees raw data it did not ask for, never runs SQL directly, and
must answer from tool results. Each step is one JSON object:

    {"action": "sql", "query": "...", "reason": "..."}
    {"action": "search_docs", "query": "...", "reason": "..."}
    {"action": "answer", "text": "...", "sources": ["table or document names"]}

JSON actions keep the loop provider-agnostic: any chat model that can follow
instructions works, with or without native function calling.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

import duckdb
import pandas as pd

from meridian.agent.catalog import schema_text
from meridian.agent.guard import GuardError, validate_sql
from meridian.agent.llm import ChatClient
from meridian.agent.retrieval import DocIndex

SYSTEM_TEMPLATE = """You are the AI Risk Analyst of Meridian Capital (a fictional lender built on real public data).
You answer questions from risk, finance, fraud and procurement stakeholders, using ONLY the tools below.

Tools (reply with exactly one JSON object per turn, nothing else):
1. {{"action": "sql", "query": "<one DuckDB SELECT>", "reason": "<why>"}}  - query the governed warehouse.
2. {{"action": "search_docs", "query": "<keywords>", "reason": "<why>"}}  - search methodology and model documentation.
3. {{"action": "answer", "text": "<final answer>", "sources": ["<tables or documents used>"]}}

Rules:
- Use only these tables. Never invent tables or columns.
- Rates in the data are shares (0.105 = 10.5%). All money columns are in USD.
- Aggregate tables must be summed before dividing (ratio of sums, not average of ratios).
- If a question cannot be answered from the tools, say so plainly. Never guess numbers.
- Final answers: 2 to 5 short sentences, lead with the number, state the period and unit, no emojis.
- Write money like a finance report: $2.97B, $475.0M, $1,746 (B for billions, M for millions), and rates as percentages with one decimal (12.2%).

Warehouse catalog:
{schema}
"""


@dataclass
class Step:
    action: str
    detail: str
    observation: str = ""


@dataclass
class AnalystResult:
    question: str
    answer: str
    steps: list[Step] = field(default_factory=list)
    last_sql: str | None = None
    last_frame: pd.DataFrame | None = None
    sources: list[str] = field(default_factory=list)


def _parse_action(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        raise ValueError("Model reply contained no JSON object.")
    return json.loads(match.group(0))


class RiskAnalyst:
    def __init__(self, con: duckdb.DuckDBPyConnection, llm: ChatClient, docs: DocIndex, max_steps: int = 5):
        self.con, self.llm, self.docs, self.max_steps = con, llm, docs, max_steps
        self.system = SYSTEM_TEMPLATE.format(schema=schema_text(con))

    def run_sql(self, sql: str) -> pd.DataFrame:
        return self.con.execute(validate_sql(sql)).df()

    def ask(self, question: str) -> AnalystResult:
        result = AnalystResult(question=question, answer="")
        messages = [{"role": "user", "content": question}]
        for _ in range(self.max_steps):
            reply = self.llm.chat(self.system, messages)
            messages.append({"role": "assistant", "content": reply})
            try:
                action = _parse_action(reply)
            except (ValueError, json.JSONDecodeError) as err:
                obs = f"Invalid reply ({err}). Reply with one JSON object."
                result.steps.append(Step("invalid", reply[:200], obs))
                messages.append({"role": "user", "content": obs})
                continue

            kind = action.get("action")
            if kind == "answer":
                result.answer = action.get("text", "").strip()
                result.sources = action.get("sources", [])
                result.steps.append(Step("answer", result.answer))
                return result
            if kind == "sql":
                sql = action.get("query", "")
                try:
                    safe = validate_sql(sql)
                    df = self.con.execute(safe).df()
                    result.last_sql, result.last_frame = safe, df
                    obs = f"{len(df)} rows. First rows:\n{df.head(20).to_csv(index=False)}"
                except GuardError as err:
                    obs = f"Blocked by guardrail: {err}"
                except duckdb.Error as err:
                    obs = f"SQL error: {str(err).splitlines()[0]}"
                result.steps.append(Step("sql", sql, obs))
            elif kind == "search_docs":
                hits = self.docs.search(action.get("query", ""), k=3)
                obs = "\n\n".join(f"[{p.source} / {p.heading}]\n{p.text[:900]}" for p, _ in hits) or "No matching documentation."
                result.steps.append(Step("search_docs", action.get("query", ""), obs))
            else:
                obs = f"Unknown action '{kind}'."
                result.steps.append(Step("invalid", str(action)[:200], obs))
            messages.append({"role": "user", "content": f"Tool result:\n{obs}"})

        result.answer = "I could not complete this analysis within the step limit. Please rephrase or narrow the question."
        return result
