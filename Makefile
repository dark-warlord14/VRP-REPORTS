.PHONY: install test lint format clean

install:
	pip install -e ".[dev]" && playwright install chromium

test:
	pytest tests/ -v

lint:
	ruff check vrp/ tests/

format:
	ruff format vrp/ tests/

clean:
	rm -rf dist/ .pytest_cache __pycache__ vrp_reports.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
