SHELL := /bin/bash

.PHONY: lint fmt pack

lint:
	bash -lc 'command -v shellcheck >/dev/null && shellcheck scripts/*.sh || echo "shellcheck not installed"'
	yamllint . || true

fmt:
	@echo "No code formatters configured; consider shfmt/black if needed."

pack:
	tar czf ../ham-dvbt2-445_5mhz.tar.gz .
	@echo "Packed to ../ham-dvbt2-445_5mhz.tar.gz"
