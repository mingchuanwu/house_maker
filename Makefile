# House maker - common tasks. Run `make` for the list.
SHELL      := /bin/bash
UV         ?= uv
REVIEW_DIR ?= /tmp/house_gallery
INBOX      ?= /tmp/house_review_inbox
# the package is the repo root, so run python tools from its parent directory when not installed
OPEN       := $(shell command -v open || command -v xdg-open || echo echo)

.DEFAULT_GOAL := help
.PHONY: help setup node-deps test test-fast build review collect feedback house clean distclean

help: ## list the targets
	@grep -E '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-11s %s\n", $$1, $$2}'
	@echo; echo "  variables: REVIEW_DIR=$(REVIEW_DIR)  INBOX=$(INBOX)"

setup: ## create .venv and install the Python dependencies (uv sync); also node-deps if npm exists
	$(UV) sync
	@command -v npm >/dev/null && $(MAKE) --no-print-directory node-deps || echo "npm not found: skipping the optional node tests"

node-deps: ## install jsdom (only needed for the review-page browser-logic tests)
	npm install --no-audit --no-fund

test: ## run the whole test suite
	$(UV) run pytest -q

test-fast: ## stop at the first failure
	$(UV) run pytest -q -x

build: ## build the wheel and sdist into dist/ (after running the tests)
	$(UV) run pytest -q
	$(UV) build
	@echo; ls -1 dist/

review: ## run the tests, write all SVGs + review.html to REVIEW_DIR and open the review page
	rm -rf $(REVIEW_DIR)
	$(UV) run pytest -q --svg-dir $(REVIEW_DIR)
	@mkdir -p $(INBOX)
	@echo; echo "Review page : $(REVIEW_DIR)/review.html"
	@echo "Save exported feedback in : $(INBOX)   (then: make feedback)"
	@$(OPEN) $(REVIEW_DIR)/review.html

collect: ## move exported feedback files from the inbox into house_maker/review/feedback/ and print them
	@$(UV) run python -m house_maker.review collect --inbox $(INBOX) || echo "(nothing to collect in $(INBOX))"

feedback: collect ## alias of collect

house: ## generate a sample house: make house ARGS="--add-chimney --angle 40"
	$(UV) run house-maker --output house_box.svg $(ARGS)

clean: ## remove caches and generated reviews
	rm -rf .pytest_cache build dist *.egg-info $(REVIEW_DIR)
	find . -name __pycache__ -type d -not -path './.venv/*' -not -path './node_modules/*' -prune -exec rm -rf {} +

distclean: clean ## also remove .venv and node_modules
	rm -rf .venv node_modules
