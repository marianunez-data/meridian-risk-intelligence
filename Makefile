# Meridian Capital, Counterparty Risk Intelligence Platform
# Run `make help` for the list of targets.

PY ?= python
export MERIDIAN_DATA ?= $(CURDIR)/data

.PHONY: help setup data bronze warehouse docs notebooks app-data app test lint eval-agent all

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-12s %s\n", $$1, $$2}'

setup:  ## Install the package and all development dependencies
	$(PY) -m pip install -r requirements-dev.txt
	$(PY) -m pip install -e .

data:  ## Download raw data (about 3 GB): Lending Club, PaySim, FRED, SEC
	$(PY) scripts/download_data.py

bronze:  ## Convert raw files to typed Parquet (bronze layer)
	$(PY) scripts/build_bronze.py

warehouse:  ## Build silver and gold layers with dbt and run all 43 data tests
	cd warehouse && dbt build --profiles-dir .

docs:  ## Generate and serve the dbt documentation site (lineage graph, column docs)
	cd warehouse && dbt docs generate --profiles-dir . && dbt docs serve --profiles-dir .

notebooks:  ## Execute every notebook in order (about 1 hour, most of it in 07 and 10)
	for nb in notebooks/*.ipynb; do \
		$(PY) -m jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=5400 $$nb || exit 1; \
	done

app-data:  ## Export the compact app warehouse (app/data/meridian_app.duckdb)
	$(PY) scripts/export_app_data.py

app:  ## Run the Streamlit dashboard locally
	streamlit run app/streamlit_app.py

test:  ## Run unit tests
	$(PY) -m pytest -q

lint:  ## Lint the Python code
	ruff check src scripts app tests

eval-agent:  ## Evaluate the AI Risk Analyst with a real LLM (needs GEMINI_API_KEY or GROQ_API_KEY)
	$(PY) scripts/eval_agent.py

all: data bronze warehouse notebooks app-data test  ## Rebuild everything from scratch
