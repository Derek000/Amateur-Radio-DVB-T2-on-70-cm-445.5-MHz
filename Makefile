SHELL := /bin/bash
.PHONY: help lint test validate check-deps tx rx tx-metrics rx-grblocks \
        encode-test watch-metrics report pack clean

PARAMS ?= params.yaml

## ── Help ─────────────────────────────────────────────────────────────────────
help:           ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	  | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-20s\033[0m %s\n",$$1,$$2}'

## ── Code quality ─────────────────────────────────────────────────────────────
lint:           ## Run shellcheck + yamllint + pyflakes
	@echo "==> shellcheck"
	shellcheck scripts/*.sh
	@echo "==> yamllint"
	yamllint .
	@echo "==> Python syntax"
	@for f in scripts/*.py grc/blocks/*.py; do \
	  python3 -c "import ast; ast.parse(open('$$f').read())" && echo "  OK  $$f" || exit 1; \
	done
	@command -v pyflakes >/dev/null && pyflakes scripts/*.py grc/blocks/*.py || true
	@echo "==> All lint checks passed"

test:           ## Run Python unit tests
	pytest tests/ -v

## ── Validation ───────────────────────────────────────────────────────────────
validate:       ## Validate params.yaml
	python3 scripts/validate_params.py --params $(PARAMS)

check-deps:     ## Check all runtime dependencies
	bash scripts/check_deps.sh

## ── Run TX / RX ──────────────────────────────────────────────────────────────
tx:             ## Build and run the TX flowgraph (headless-safe)
	bash scripts/run_tx.sh --params $(PARAMS)

tx-metrics:     ## Build and run TX with MER/EVM metrics logging
	bash scripts/run_tx.sh --params $(PARAMS) --metrics

rx:             ## Build and run the RX flowgraph (headless-safe)
	bash scripts/run_rx.sh --params $(PARAMS)

rx-grblocks:    ## Build and run the gr-dvbs2rx all-blocks RX variant
	bash scripts/run_rx.sh --params $(PARAMS) --grblocks

## ── Test card ────────────────────────────────────────────────────────────────
encode-test:    ## Stream a 60-second synthetic test card to UDP TX input
	bash scripts/encode_h264_ts.sh --test-card

## ── Metrics ──────────────────────────────────────────────────────────────────
report:         ## Generate MER/EVM HTML report from metrics CSV
	python3 scripts/plot_metrics.py --csv metrics/tx_metrics.csv --outdir reports
	@echo "Open reports/index.html"

watch-metrics:  ## Watch and auto-refresh the HTML report as the CSV grows
	python3 scripts/plot_metrics.py --csv metrics/tx_metrics.csv --outdir reports --watch

status:         ## Live terminal MER/EVM dashboard (requires: pip install rich)
	python3 scripts/status_monitor.py --csv metrics/tx_metrics.csv

## ── Link budget ──────────────────────────────────────────────────────────────
budget:         ## Print link budget using params.yaml (edit params or use DIST=km)
	python3 scripts/link_budget.py --params $(PARAMS) --distance $(or $(DIST),5)

## ── Packaging ────────────────────────────────────────────────────────────────
pack:           ## Create a distributable tar.gz of the project
	tar czf ../ham-dvbt2-445_5mhz.tar.gz \
	  --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' \
	  --exclude='metrics' --exclude='reports' \
	  . && echo "Packed to ../ham-dvbt2-445_5mhz.tar.gz"

## ── Clean ────────────────────────────────────────────────────────────────────
clean:          ## Remove generated Python files and build artefacts
	find grc -name '*.py' ! -path 'grc/blocks/*' -delete
	rm -rf reports __pycache__ grc/__pycache__ scripts/__pycache__
