"""The committed app warehouse must contain every table the dashboard and the agent use."""
import duckdb
import pytest

from meridian import config
from meridian.agent.catalog import TABLES
from meridian.agent.evaluate import load_eval_set
from meridian.agent.guard import validate_sql

pytestmark = pytest.mark.skipif(not config.APP_DB_PATH.exists(), reason="app warehouse not built")


@pytest.fixture(scope="module")
def con():
    return duckdb.connect(str(config.APP_DB_PATH), read_only=True)


def test_governed_tables_exist(con):
    existing = {r[0] for r in con.execute("select table_name from information_schema.tables").fetchall()}
    assert set(TABLES) <= existing


@pytest.mark.parametrize("item", load_eval_set(), ids=lambda i: i["id"])
def test_every_gold_query_runs_and_returns_rows(con, item):
    assert len(con.execute(validate_sql(item["gold_sql"])).df()) > 0
