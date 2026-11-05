# The parent repository: it pins Common-Components, Core, Memory and Peripherals, and
# this Makefile runs them together. Each of them has its own Makefile and uv project;
# `git submodule update --init --recursive` first. The riscv-tools command comes from
# the toolchain image of insper-riscv/Infra.
SHELL := /bin/bash

SUBREPOS := Common-Components Core Memory Peripherals
# Core, Memory and Peripherals carry their own copy of Common-Components as a submodule
# (Core in src/common since its R.1 layout).
NESTED   := ! -path 'Core/src/common/*' ! -path 'Memory/src/common/*' ! -path 'Peripherals/src/common/*'
# The platforms of this repository: the simulation-only one and the board one.
P  := src/simulation/internal-mem
PF := src/cyclone-v/de0-cv
PM := src/simulation/modular
GHDL := ghdl
STD  := --std=08
WDIR := build/ghdl

# The UART of Peripherals is part of the simulation tops.
UART_VHDL := Peripherals/src/UART/serial/vendor/opencores_uart2bus/uart2BusTop_pkg.vhd \
             Peripherals/src/UART/serial/vendor/opencores_uart2bus/baudGen.vhd \
             Peripherals/src/UART/serial/vendor/opencores_uart2bus/uartRx.vhd \
             Peripherals/src/UART/serial/vendor/opencores_uart2bus/uartTx.vhd \
             Peripherals/src/UART/serial/vendor/opencores_uart2bus/uartTop.vhd \
             Peripherals/src/UART/serial/uart_fifo.vhd \
             Peripherals/src/UART/serial/uart.vhd

# The simulation top of internal-mem (rv32i3stage_core_sim_test): the core with the simulation memories and peripherals.
SIM_VHDL := $(shell find Common-Components/src Core/src -name '*.vhd' -not -path 'Core/src/common/*' | sort) \
            Memory/src/RAM/SoC/ram_simulation.vhd Memory/src/ROM/SoC/rom_simulation.vhd \
            $(UART_VHDL) $(P)/rtl/clk_gen_3way.vhd $(P)/rtl/internal_mem_map_pkg.vhd \
            $(P)/rtl/rv32i3stage_core_sim_test.vhd

# The simulation top of the board platform adds the SDRAM, the caches, the FLASH chip and the region router of Memory, and the
# external interconnect of this repository.
BOARD_VHDL := $(shell find src/interconnect Memory/src/RAM/SoC Memory/src/RAM/FPGA/debug Memory/src/barramento/SoC Peripherals/src/UART/jtag Peripherals/src/display/soc -name '*.vhd' -not -path '*/cyclone-v/*' -not -name ram_simulation.vhd | sort) \
               $(addprefix Memory/src/cache/SoC/,icache.vhd dcache.vhd flash_chip.vhd flash_arbiter.vhd mem_region_router.vhd) \
               $(PF)/de0_cv_map_pkg.vhd $(PF)/de0-cv_sim_top.vhd

# What is not a source of the design: tests, proofs, vendor code, build output and the Quartus IPs.
NOT_RTL  := ! -path '*/tests/*' ! -path '*/formal/*' ! -path '*/vendor/*' ! -path '*/build/*' ! -path '*/hw/*' ! -path '*/quartus/*' ! -path '*/.git/*'

.PHONY: all sync paths check check-tops check-unique memory-map generate generate-check test unit-tests formal clean

all: paths check unit-tests formal

sync:
	@set -e; uv sync -q; for s in $(SUBREPOS); do (cd $$s && uv sync -q); done

# Every file path that the configuration of each repository lists exists (the paths.yaml of each one),
# and the ones of this repository (its platforms included), and the tree has the shape the Capstone defines.
paths:
	@set -e; for s in $(SUBREPOS); do $(MAKE) -C $$s paths; done
	riscv-tools --root . check-paths --manifest paths.yaml
	riscv-tools --root . check-tree --kind top

# VHDL syntax check (GHDL) of every repository (the Core also elaborates each of its profiles), of the two
# simulation tops of the platforms and the uniqueness of the names.
check:
	$(MAKE) -C Common-Components check
	$(MAKE) -C Core profiles
	$(MAKE) -C Memory check
	$(MAKE) -C Peripherals check
	$(MAKE) check-tops
	$(MAKE) check-unique

# GHDL analyzes and elaborates the simulation top of each platform. The ROM models open their image when
# they are elaborated (default.hex, from their generic), so a one-word one is put in the work directory.
check-tops:
	@mkdir -p $(WDIR)
	@$(GHDL) -a $(STD) --work=work --workdir=$(WDIR) $$(riscv-tools vhdl-sort $(SIM_VHDL))
	@printf '00000000\n' > $(WDIR)/default.hex
	@cd $(WDIR) && $(GHDL) -e $(STD) --workdir=. rv32i3stage_core_sim_test
	@echo "the simulation top of internal-mem builds"
	@$(GHDL) -a $(STD) --work=work --workdir=$(WDIR) $$(riscv-tools vhdl-sort $(SIM_VHDL) $(BOARD_VHDL))
	@cd $(WDIR) && $(GHDL) -e $(STD) --workdir=. rv32im_sdram_flash_sim_test
	@echo "the simulation top of the de0-cv platform builds"

# No entity or package is defined in two repositories: they would clash in the library of any design
# that uses both.
check-unique:
	@dups=$$(find $(SUBREPOS) -name '*.vhd' $(NESTED) $(NOT_RTL) -print0 \
	  | xargs -0 grep -HioE '^[[:space:]]*(entity|package)[[:space:]]+[A-Za-z0-9_]+[[:space:]]+is' \
	  | sed -E 's/^([^:]+):[[:space:]]*(entity|package)[[:space:]]+([A-Za-z0-9_]+).*/\3 \1/I' \
	  | awk '{n = tolower($$1); c[n]++; f[n] = f[n] " " $$2} END {for (k in c) if (c[k] > 1) print k ":" f[k]}'); \
	if [ -n "$$dups" ]; then echo "defined more than once:"; echo "$$dups"; exit 1; fi; \
	echo "no entity or package is defined twice"

# Every copy of the memory map (config, linker flags, boot ROM, runtime, the core's VHDL, the Quartus IPs)
# agrees with platform.yaml, in each platform.
memory-map:
	riscv-tools --root . check-memory-map --platform $(P)/platform.yaml
	riscv-tools --root . check-memory-map --platform $(PF)/platform.yaml
	$(MAKE) generate-check

# The files written from the map of each platform (the linker flags, the linker script of the boot ROM and
# the VHDL package of the generics): `make generate` writes them and `make generate-check` fails when one
# is out of date.
generate:
	riscv-tools --root . generate-memory-map --platform $(P)/platform.yaml
	riscv-tools --root . generate-memory-map --platform $(PF)/platform.yaml
	riscv-tools --root . generate-memory-map --platform $(PM)/platform.yaml

generate-check:
	riscv-tools --root . generate-memory-map --platform $(P)/platform.yaml --check
	riscv-tools --root . generate-memory-map --platform $(PF)/platform.yaml --check
	riscv-tools --root . generate-memory-map --platform $(PM)/platform.yaml --check

# Per-entity cocotb tests of the RTL of the platforms (`make test TEST=clk_gen_3way`).
test:
	uv run python tests/python/runner.py $(TEST)

# The per-entity cocotb tests of each repository and of the platforms, and the memory map check.
unit-tests: sync memory-map test
	$(MAKE) -C Common-Components test
	$(MAKE) -C Core test
	$(MAKE) -C Memory test
	$(MAKE) -C Peripherals test

# Every make target named formal* of each repository (SymbiYosys; FORMAL_ENGINE=yices, bitwuzla, boolector or
# abc-bmc3 on the command line goes to each of them), all at once: each proof works in
# its own folder, so none shares anything with another, and the time is the one of the longest proof instead
# of the sum. A repository without proofs adds nothing. -k lets the others finish when one fails and -O keeps
# the output of each target together.
FORMAL_JOBS := $(strip $(foreach s,$(SUBREPOS),$(addprefix formal/$(s)/,$(shell sed -n 's/^\(formal[a-z-]*\):.*/\1/p' $(s)/Makefile 2>/dev/null))))

.PHONY: formal formal-run $(FORMAL_JOBS)

formal:
	@test -n "$(FORMAL_JOBS)" || { echo "no formal target in $(SUBREPOS)"; exit 1; }
	$(MAKE) -k -O -j$(words $(FORMAL_JOBS)) formal-run

formal-run: $(FORMAL_JOBS)

$(FORMAL_JOBS): formal/%:
	$(MAKE) -C $(word 1,$(subst /, ,$*)) $(word 2,$(subst /, ,$*))

clean:
	rm -rf build
	find . -path ./.git -prune -o -type f \( -name '*.vcd' -o -name '*.ghw' \) -print -delete
