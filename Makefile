.PHONY: install uninstall test lint typecheck format check

install:
	uv tool install --force --from . alm-scraper
	@echo "Installed alm to ~/.local/bin/alm"

uninstall:
	uv tool uninstall alm-scraper
	@echo "Uninstalled alm-scraper"

test:
	uv run pytest

lint:
	uv run ruff check src/ tests/

typecheck:
	uv run ty check src/

format:
	uv run ruff format .

check: lint typecheck test
