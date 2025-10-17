SHELL := /bin/bash
.PHONY: lint pack
lint:
	bash -lc 'command -v shellcheck >/dev/null && shellcheck scripts/*.sh || echo "shellcheck not installed"'
	yamllint . || true
pack:
	tar czf ../ham-dvbt2-445_5mhz.tar.gz . && echo "Packed to ../ham-dvbt2-445_5mhz.tar.gz"
