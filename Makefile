# The parent repository: it pins Common-Components, Core, Memory and Peripherals, and
# this Makefile runs only what is its own or integrates them (each submodule runs its own checks, tests and proofs in its CI). Each of them has its own Makefile and uv project;
# `git submodule update --init --recursive` first. The riscv-tools command comes from
# the toolchain image of insper-riscv/Infra.
SHELL := /bin/bash

SUBREPOS := Common-Components Core Memory Peripherals
# Core, Memory and Peripherals carry their own copy of Common-Components as a submodule
# (Core in src/common since its R.1 layout).
NESTED   := ! -path 'Core/src/common/*' ! -path 'Memory/src/common/*' ! -path 'Peripherals/src/common/*'
# The platforms of this repository: the simulation-only ones and the board ones.
P  := src/simulation/internal-mem
PF := src/cyclone-v/de0-cv
PE := src/cyclone-v/external-data
PM := src/simulation/modular
PT := src/simulation/template
# The platforms of the two small boards: the reduced profile of the DE0-Nano and the full profile of the DE10-Lite.
PN := src/cyclone-iv-e/de0-nano
PL := src/max-10/de10-lite
# The ten platforms of the family (four for the tests, four on the board, two for the UART): one directory each, with its
# platform.yaml, and all of them run the same modular_sim_top (the sources of one are `sources <name>_map modular_sim_top`).
TEN := test-integrated test-external-data test-external-instruction test-external \
  fpga-integrated fpga-external-data fpga-external-instruction fpga-external fpga-uart-jtag fpga-uart-pins
# The directory of platform $$n of TEN, for a shell loop of a recipe.
TEN_DIR = $$(case $$n in test-*) echo src/simulation;; *) echo src/cyclone-v;; esac)/$$n
GHDL := ghdl
STD  := --std=08
WDIR := build/ghdl
# The source files of a top, in analysis order, from the provides of this repository and of its submodules.
SOURCES := riscv-tools --root . sources

# What is not a source of the design: tests, proofs, vendor code, build output and the Quartus IPs.
NOT_RTL  := ! -path '*/tests/*' ! -path '*/formal/*' ! -path '*/vendor/*' ! -path '*/build/*' ! -path '*/hw/*' ! -path '*/quartus/*' ! -path '*/.git/*'

.PHONY: all sync paths check check-tops check-generics check-irq-sources check-unique memory-map generate generate-check generate-sources sources-check test unit-tests formal clean

all: paths check unit-tests formal

sync:
	@set -e; uv sync -q; for s in $(SUBREPOS); do (cd $$s && uv sync -q); done

# Every file path that the configuration of this repository lists exists (its paths.yaml, its platforms
# included), and the tree has the shape the Capstone defines. The paths of the submodules are checked in
# the CI of each one.
paths:
	riscv-tools --root . check-paths --manifest paths.yaml
	riscv-tools --root . check-tree --kind top
	riscv-tools --root . check-boards

# What only this repository can check: the two simulation tops of the platforms build with the pinned
# submodules and no name is defined twice across them. The VHDL syntax of each submodule (and the profiles of
# the Core) is checked in the CI of each one.
check: sources-check check-tops check-generics check-unique check-irq-sources

# GHDL analyzes and elaborates the simulation top of each platform. The ROM models open their image when
# they are elaborated (default.hex, from their generic), so a one-word one is put in the work directory.
check-tops:
	@mkdir -p $(WDIR)
	@$(GHDL) -a $(STD) --work=work --workdir=$(WDIR) $$($(SOURCES) internal_mem_sim_top)
	@printf '00000000\n' > $(WDIR)/default.hex
	@cd $(WDIR) && $(GHDL) -e $(STD) --workdir=. rv32i3stage_core_sim_test
	@echo "the simulation top of internal-mem builds"
	@$(GHDL) -a $(STD) --work=work --workdir=$(WDIR) $$($(SOURCES) de0_cv_sim_top)
	@cd $(WDIR) && $(GHDL) -e $(STD) --workdir=. rv32im_sdram_flash_sim_test
	@echo "the simulation top of the de0-cv platform builds"
	@$(GHDL) -a $(STD) --work=work --workdir=$(WDIR) $$($(SOURCES) external_data_sim_top)
	@cd $(WDIR) && $(GHDL) -e $(STD) --workdir=. rv32im_external_data_sim_test
	@echo "the simulation top of the external-data platform builds"
	@$(GHDL) -a $(STD) --work=work --workdir=$(WDIR) $$($(SOURCES) template_sim_top)
	@cd $(WDIR) && $(GHDL) -e $(STD) --workdir=. template_sim_top
	@echo "the simulation top of the template platform builds"
	@$(GHDL) -a $(STD) --work=work --workdir=$(WDIR) $$($(SOURCES) modular_map modular_sim_top)
	@cd $(WDIR) && $(GHDL) -e $(STD) --workdir=. modular_sim_top
	@echo "the simulation top of the modular platform builds"
	@for n in $(TEN); do \
	  rm -rf $(WDIR)/ten && mkdir -p $(WDIR)/ten && \
	  $(GHDL) -a $(STD) --work=work --workdir=$(WDIR)/ten $$($(SOURCES) $$(echo $$n | tr - _)_map modular_sim_top) && \
	  (cd $(WDIR)/ten && $(GHDL) -e $(STD) --workdir=. modular_sim_top) || exit 1; \
	  echo "the simulation top of the $$n platform builds"; \
	done

# Every HAS_* constant of the generated package of a platform is a generic of its tops: the generics
# that the generate step and riscv-tools platform sync pass to GHDL must exist there.
check-generics:
	python3 scripts/check_top_generics.py

# The numbers of the PLIC sources of the modular top and of every platform.yaml agree.
check-irq-sources:
	uv run --no-project --with pyyaml python scripts/check_irq_sources.py

# No entity or package is defined in two repositories: they would clash in the library of any design
# that uses both.
check-unique:
	@dups=$$(find $(SUBREPOS) -name '*.vhd' $(NESTED) $(NOT_RTL) -print0 \
	  | xargs -0 grep -HioE '^[[:space:]]*(entity|package)[[:space:]]+[A-Za-z0-9_]+[[:space:]]+is' \
	  | sed -E 's/^([^:]+):[[:space:]]*(entity|package)[[:space:]]+([A-Za-z0-9_]+).*/\3 \1/I' \
	  | awk '{n = tolower($$1); c[n]++; f[n] = f[n] " " $$2} END {for (k in c) if (c[k] > 1) print k ":" f[k]}'); \
	if [ -n "$$dups" ]; then echo "defined more than once:"; echo "$$dups"; exit 1; fi; \
	echo "no entity or package is defined twice"

# Every copy of the memory map (config, linker flags, boot memory, runtime, the core's VHDL, the Quartus IPs)
# agrees with platform.yaml, in each platform.
memory-map:
	riscv-tools --root . check-memory-map --platform $(P)/platform.yaml
	riscv-tools --root . check-memory-map --platform $(PF)/platform.yaml
	riscv-tools --root . check-memory-map --platform $(PE)/platform.yaml
	riscv-tools --root . check-memory-map --platform $(PM)/platform.yaml
	riscv-tools --root . check-memory-map --platform $(PT)/platform.yaml
	riscv-tools --root . check-memory-map --platform $(PN)/platform.yaml
	riscv-tools --root . check-memory-map --platform $(PL)/platform.yaml
	@for n in $(TEN); do riscv-tools --root . check-memory-map --platform $(TEN_DIR)/platform.yaml || exit 1; done
	$(MAKE) generate-check sources-check

# The files written from the map of each platform (the linker flags, the linker script of the boot memory and
# the VHDL package of the generics): `make generate` writes them and `make generate-check` fails when one
# is out of date.
generate:
	riscv-tools --root . generate-memory-map --platform $(P)/platform.yaml
	riscv-tools --root . generate-memory-map --platform $(PF)/platform.yaml
	riscv-tools --root . generate-memory-map --platform $(PE)/platform.yaml
	riscv-tools --root . generate-memory-map --platform $(PM)/platform.yaml
	riscv-tools --root . generate-memory-map --platform $(PT)/platform.yaml
	riscv-tools --root . generate-memory-map --platform $(PN)/platform.yaml
	riscv-tools --root . generate-memory-map --platform $(PL)/platform.yaml
	@for n in $(TEN); do riscv-tools --root . generate-memory-map --platform $(TEN_DIR)/platform.yaml || exit 1; done

generate-check:
	riscv-tools --root . generate-memory-map --platform $(P)/platform.yaml --check
	riscv-tools --root . generate-memory-map --platform $(PF)/platform.yaml --check
	riscv-tools --root . generate-memory-map --platform $(PE)/platform.yaml --check
	riscv-tools --root . generate-memory-map --platform $(PM)/platform.yaml --check
	riscv-tools --root . generate-memory-map --platform $(PT)/platform.yaml --check
	riscv-tools --root . generate-memory-map --platform $(PN)/platform.yaml --check
	riscv-tools --root . generate-memory-map --platform $(PL)/platform.yaml --check
	@for n in $(TEN); do riscv-tools --root . generate-memory-map --platform $(TEN_DIR)/platform.yaml --check || exit 1; done

# The source lists of the tops (the config*.yaml, tests/python/tests.json and the .qsf files) come from the
# provides of the repositories, through `riscv-tools sources`: `make generate-sources` writes them and
# `make sources-check` fails when one is out of date. A new file of a submodule enters the tops through
# the provides of that submodule, never by editing a list here.
generate-sources:
	uv run --no-project python scripts/generate_sources.py

sources-check:
	uv run --no-project python scripts/generate_sources.py --check

# Per-entity cocotb tests of the RTL of the platforms (`make test TEST=clk_gen_3way`).
test:
	uv run python tests/python/runner.py $(TEST)

# The per-entity cocotb tests of this repository (the platforms) and the memory map check. The tests of
# Common-Components, Core, Memory and Peripherals run in the CI of each one (`make test` there), not here.
unit-tests: sync memory-map test

# The formal proofs of this repository only: the external interconnect (src/interconnect), with the engine
# FORMAL_ENGINE (yices, bitwuzla, boolector or abc-bmc3; bitwuzla by default). The proofs of the submodules
# run in the CI of each one. FORMAL_JOBS is empty by construction and stays as the list of the proofs
# of the submodules that this repository does not run. Each proof works in its own folder, -k lets the
# others finish when one fails and -O keeps the output of each target together.
FORMAL_JOBS :=

.PHONY: formal formal-run formal-interconnect

formal:
	$(MAKE) -k -O -j$(words $(FORMAL_JOBS) formal-interconnect) formal-run

formal-run: $(FORMAL_JOBS) formal-interconnect

# The proofs of this repository: the external interconnect (src/interconnect), whose result is
# build/formal/result-<engine>.tsv, read by formal/aggregate.sh.
formal-interconnect:
	FORMAL_ENGINE=$(FORMAL_ENGINE) bash formal/interconnect.sh

clean:
	rm -rf build
	find . -path ./.git -prune -o -type f \( -name '*.vcd' -o -name '*.ghw' \) -print -delete
