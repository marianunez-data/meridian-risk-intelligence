"""Render every dashboard page headlessly and fail on any exception (run in CI)."""
from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py"
PAGES = sorted(p.name for p in (APP.parent / "views").glob("*.py") if p.name != "__init__.py")

failed = []
for page in PAGES:
    at = AppTest.from_file(str(APP), default_timeout=240)
    at.run()
    at.switch_page(f"views/{page}").run()
    if at.exception:
        failed.append((page, at.exception[0].value))
    print(f"{page:<24} {'FAIL' if at.exception else 'ok'}")
if failed:
    raise SystemExit(f"{len(failed)} page(s) failed: {failed}")
