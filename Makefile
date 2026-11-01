# The parent repository: it pins Core, Memory, Peripherals, TopLevel and Tests, and
# this Makefile runs them together. Each of them has its own Makefile and uv project;
# `git submodule update --init --recursive` first. The repositories sit side by side
# here, which is how their own Makefiles and configurations name each other (../Core).
# The riscv-tools command comes from the toolchain image of insper-riscv/Infra.
SHELL := /bin/bash

SUBREPOS := Core Memory Peripherals TopLevel
# The Python of the image where riscv_tools is installed (the host tests of Tests import it).
PYTOOLS  ?= /opt/riscv-tools/riscv-tools/bin/python

.PHONY: all sync paths check unit-tests formal sim clean

all: paths check unit-tests formal sim

sync:
	@set -e; for s in $(SUBREPOS) Tests; do (cd $$s && uv sync -q); done

# Every file path that the configuration of each repository lists exists (the paths.yaml of each one).
paths:
	@set -e; for s in $(SUBREPOS); do $(MAKE) -C $$s paths; done

# VHDL syntax check (GHDL) of every repository, in dependency order. The TopLevel analyzes the sources of
# Common-Components, Core, Memory and Peripherals together in one library, so it also catches two
# repositories defining the same entity; the Core also elaborates each of its profiles.
check:
	$(MAKE) -C Core profiles
	$(MAKE) -C Memory check
	$(MAKE) -C Peripherals check
	$(MAKE) -C TopLevel check

# The per-entity cocotb tests of each repository, and the memory map check of the TopLevel.
unit-tests: sync
	$(MAKE) -C Core test
	$(MAKE) -C Memory test
	$(MAKE) -C Peripherals test
	$(MAKE) -C TopLevel memory-map test

# Every make target named formal* of each repository (SymbiYosys and z3); a repository without proofs is skipped.
formal:
	@set -e; for s in $(SUBREPOS); do \
	  for t in $$(sed -n 's/^\(formal[a-z-]*\):.*/\1/p' $$s/Makefile); do $(MAKE) -C $$s $$t; done; \
	done

# The Tests project's generic simulation suite, including uart-tx, uart-echo
# and uart-errors through the generic top's serial pins.
sim: sync
	cd Tests && $(PYTOOLS) -m unittest discover -s tests/host -v \
	  && riscv-tools --config tools/riscv_build/config.yaml generate-header \
	  && riscv-tools --config tools/riscv_build/config.yaml compile --emit hex \
	  && riscv-tools --config tools/riscv_build/config.yaml sim

clean:
	rm -rf build
	find . -path ./.git -prune -o -type f \( -name '*.vcd' -o -name '*.ghw' \) -print -delete
