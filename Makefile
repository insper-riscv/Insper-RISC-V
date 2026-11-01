# The parent repository: it pins Common-Components, Core, Memory and Peripherals, and
# this Makefile runs them together. Each of them has its own Makefile and uv project;
# `git submodule update --init --recursive` first. The riscv-tools command comes from
# the toolchain image of insper-riscv/Infra.
SHELL := /bin/bash

SUBREPOS := Common-Components Core Memory Peripherals
# Core, Memory and Peripherals carry their own copy of Common-Components as a submodule.
NESTED   := ! -path 'Core/Common-Components/*' ! -path 'Memory/Common-Components/*' ! -path 'Peripherals/Common-Components/*'
# What is not a source of the design: tests, proofs, vendor code, build output and the Quartus IPs.
NOT_RTL  := ! -path '*/tests/*' ! -path '*/formal/*' ! -path '*/vendor/*' ! -path '*/build/*' ! -path '*/hw/*' ! -path '*/quartus/*' ! -path '*/.git/*'

.PHONY: all sync paths check check-unique unit-tests formal sim clean

all: paths check unit-tests formal sim

sync:
	@set -e; for s in $(SUBREPOS); do (cd $$s && uv sync -q); done

# Every file path that the configuration of each repository lists exists (the paths.yaml of each one),
# and the ones of this repository.
paths:
	@set -e; for s in $(SUBREPOS); do $(MAKE) -C $$s paths; done
	riscv-tools --root . check-paths --manifest paths.yaml

# VHDL syntax check (GHDL) of every repository; the Core also elaborates each of its profiles.
check:
	$(MAKE) -C Common-Components check
	$(MAKE) -C Core profiles
	$(MAKE) -C Memory check
	$(MAKE) -C Peripherals check
	$(MAKE) check-unique

# No entity or package is defined in two repositories: they would clash in the library of any design
# that uses both.
check-unique:
	@dups=$$(find $(SUBREPOS) -name '*.vhd' $(NESTED) $(NOT_RTL) -print0 \
	  | xargs -0 grep -HioE '^[[:space:]]*(entity|package)[[:space:]]+[A-Za-z0-9_]+[[:space:]]+is' \
	  | sed -E 's/^([^:]+):[[:space:]]*(entity|package)[[:space:]]+([A-Za-z0-9_]+).*/\3 \1/I' \
	  | awk '{n = tolower($$1); c[n]++; f[n] = f[n] " " $$2} END {for (k in c) if (c[k] > 1) print k ":" f[k]}'); \
	if [ -n "$$dups" ]; then echo "defined more than once:"; echo "$$dups"; exit 1; fi; \
	echo "no entity or package is defined twice"

# The per-entity cocotb tests of each repository.
unit-tests: sync
	$(MAKE) -C Common-Components test
	$(MAKE) -C Core test
	$(MAKE) -C Memory test
	$(MAKE) -C Peripherals test

# Every make target named formal* of each repository (SymbiYosys and z3); a repository without proofs is skipped.
formal:
	@set -e; for s in $(SUBREPOS); do \
	  for t in $$(sed -n 's/^\(formal[a-z-]*\):.*/\1/p' $$s/Makefile); do $(MAKE) -C $$s $$t; done; \
	done

# The programs run on a platform, and the platform joins this repository with the fold of the TopLevel.
# Until then the suite of programs runs in the Tests repository, which builds against this one.
sim:
	@echo "sim: this repository has no platform yet; the programs run in the Tests repository"

clean:
	rm -rf build
	find . -path ./.git -prune -o -type f \( -name '*.vcd' -o -name '*.ghw' \) -print -delete
