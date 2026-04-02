# Makefile

run:
	uv run uvicorn example:app --workers 1 --reload --use-colors --log-level debug --host 0.0.0.0 --port 8088

pre-commit:
	uv run pre-commit run --all-files

format:
	uv run ruff format

chek_code:
	uv run ruff check .

fix_imports:
	uv run ruff check . --fix

test:
	uv run pytest tests -s -v -x


build_project:
	uv run hatch build

publish_pip:
	uv run hatch publish