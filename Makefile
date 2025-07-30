# On windows
#   Install MSYS2 https://www.msys2.org/
#   SET PATH=%PATH%;C:\msys64\usr\bin;C:\msys64
#   (to install make: pacmman -S make)

ROOT_DIR := $(dir $(realpath $(lastword $(MAKEFILE_LIST))))

export PYTHONPATH=$(ROOT_DIR)/src


# self-documentation magic
help: ## Display the list of available targets
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'


.PHONY: check
check: check-fmt lint ## ruff check + lint
	@echo "🟢 pass"

.PHONY: check-fmt
check-fmt:  ## Runs ruff check
	@ruff check src tests && echo "🟢 ruff check pass"

.PHONY: fmt
fmt:  ## Format code (ruff check --fix), updating source files
	@ruff check --fix src tests
	@ruff format src tests

.PHONY: lint
lint:  ## Runs the linter (mypy) and report errors.
	@mypy src tests && echo "🟢 mypy check pass"


.PHONY: test
test: ## Run test suite (make test MINER=IP.ADDRESS will run against a miner)
	@pytest -vvs \
        --cov-report=html:build/coverage --cov-report=xml:build/coverage.xml \
        --junitxml=build/junit.xml --html=build/junit.html --self-contained-html \
        --cov=luxos \
        --manual tests
	@echo
	@echo "👉"
	@echo "👉 coverage and junit reports under:"
	@echo "👉    build/junit.html"
	@echo "👉    build/coverage/index.html"
	@echo "👉"


.PHONY: clean
clean:  ## cleanup
	rm -rf build .mypy_cache .pytest_cache .ruff_cache .coverage dist
	find . -type d -name __pycache__ -prune -exec rm -rf "{}" \;
	@echo "cleaned"

.PHONY: clean-all
clean-all:  clean ## deepest cleanup
	@echo "deeply cleaned"


.PHONY: docs
docs:  ## build documentation
	@python -m sphinx docs build/docs

.PHONY: serve
serve:  ## start a documentation server with autoreload
	@python -m sphinx_autobuild --watch src/luxos docs build/docs

.PHONY: publish
publish:  ## publish pages to github
	@python support/publish.py --commit build/gh-pages && rm -rf build/gh-pages

build:
	rm -rf dist
	@python -m build
