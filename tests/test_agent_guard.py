import pytest

from meridian.agent.guard import GuardError, validate_sql

ALLOWED = [
    "select grade, sum(loans) from portfolio_cube group by 1",
    "with a as (select * from portfolio_cube) select count(*) from a",
]
BLOCKED = [
    "drop table portfolio_cube",
    "select 1; drop table portfolio_cube",
    "select * from read_csv('/etc/passwd')",
    "select * from 'data/raw/file.csv'",
    "select * from applicant_sample",
    "attach 'other.duckdb' as x",
    "copy portfolio_cube to 'leak.csv'",
    "select getenv('GEMINI_API_KEY')",
    "select * from main.portfolio_cube",
    "install httpfs",
    "pragma database_list",
    "update portfolio_cube set loans = 0",
]


@pytest.mark.parametrize("sql", ALLOWED)
def test_valid_queries_pass_with_row_limit(sql):
    out = validate_sql(sql)
    assert "LIMIT 500" in out.upper()


@pytest.mark.parametrize("sql", BLOCKED)
def test_attacks_are_blocked(sql):
    with pytest.raises(GuardError):
        validate_sql(sql)


def test_oversized_limit_is_reduced():
    assert "LIMIT 500" in validate_sql("select * from portfolio_cube limit 100000").upper()
