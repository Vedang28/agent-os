.PHONY: install lint test run

install:
	python -m venv .venv
	.venv/bin/pip install -e ".[dev]"

lint:
	ruff check .
	black --check .

test:
	PYTHONPATH=. pytest -v

run:
	PYTHONPATH=. python -c "from core.graph import build_graph; g = build_graph(); print(g.invoke({'request': 'hello'}))"
