.PHONY: install uninstall test lint typecheck format check build-ui dev-ui

install: build-ui
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

# Build SvelteKit UI and copy to Python package
build-ui:
	cd ui && npm install && npm run build
	rm -rf src/alm_scraper/ui/static
	cp -r ui/build src/alm_scraper/ui/static
	@echo "Built UI to src/alm_scraper/ui/static"

# Run SvelteKit dev server (for frontend development)
dev-ui:
	cd ui && npm run dev
