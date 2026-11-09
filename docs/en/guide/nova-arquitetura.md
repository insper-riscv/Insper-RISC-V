# How to create a new architecture in Insper-RISC-V

This guide takes a clean clone of `Insper-RISC-V` to a new platform running in simulation, with its program running in the test project and its profile certified, and, if there is a board, to the FPGA. A platform is a folder `src/<family>/<platform>/` with its memory map, its selection of memories and peripherals and its Core profile. The running example is called `exemplo`, in the `simulation` family, with a 64 KiB RAM and the `rv32im` profile in place of the `rv32i` of the model platform. Chapters 11 and 12 add a peripheral and a memory type, chapter 13 takes the set to a pull request, and chapter 14 gathers the reference.

## 1. What a platform is

### 1.1. The blocks

| Block | Repository | What it provides |
| :--- | :--- | :--- |
| Core | `Core` | The processor, chosen by a profile (base `rv32i` or `rv32e` plus the extensions) |
| Memory | `Memory` | BOOT_MEMORY, ROM and FLASH (including the two-port FLASH), RAM and SDRAM, caches, FLASH chip and region router |
| Peripherals | `Peripherals` | UART, GPIO, timer, CLINT, external interrupt controller, FLASH controller and display, each with a `soc` side (family independent) and, when needed, a per-family side |
| Common-Components | `Common-Components` | Multiplexers, registers and utility packages, present as a submodule in the other three |
| Insper-RISC-V | this repository | Pins the version of each submodule and holds the platforms, which connect the blocks |

### 1.2. What the platform contains

| File | Written by | Content |
| :--- | :--- | :--- |
| `platform.yaml` | Person | Source of the memory map, the Core profile, the reserved words and the peripherals, and the list of files to generate |
| `rtl/<platform>_map_pkg.vhd` | `riscv-tools generate-memory-map` | VHDL constants of the map and the profile |
| `runtime/rv32im-fpga.specs`, `runtime/boot_memory.ld`, `runtime/memory_map.h` | `riscv-tools generate-memory-map` | Linker parameters, BOOT_MEMORY linker script and runtime addresses |
| `rtl/<platform>_sim_top.vhd` | Person | Simulation top, which only instantiates and connects the blocks |
| `runtime/boot_memory.S`, `_exit.c`, `stdio.c`, `spike_exit.S` | Person | What the program finds on start and on exit |
| `config.yaml` | Person | `riscv-tools` configuration to compile and simulate, which reads the map from `platform.yaml` |

No number of the map is written in two places. What the `config.yaml` and `Tests` need from the map reaches them through the `platform.yaml`.

### 1.3. Reference platforms

| Platform | Path | When to copy |
| :--- | :--- | :--- |
| `template` | `src/simulation/template/` | Starting point of a simulation-only platform, with BOOT_MEMORY, ROM and RAM inside the chip |
| `external-data` | `src/cyclone-v/external-data/` | Starting point of a DE0-CV board, with the two-port FLASH inside the FPGA and the SDRAM behind the data cache |
| `de0-cv` | `src/cyclone-v/de0-cv/` | Complete DE0-CV board, with the FLASH as a chip behind the instruction and data caches |

The model platform has this shape.

```text
  BOOT_MEMORY 4 KiB  --+
  ROM 28 KiB      --+--  núcleo (perfil do platform.yaml)  --  RAM 32 KiB
  (duas portas)                     |
                                    +-- janela de periféricos (bit 31 = 1) -- UART sobre JTAG (id 4)
```

## 2. Prepare the environment

### 2.1. Clone

```bash
git clone --recurse-submodules git@github.com:insper-riscv/Insper-RISC-V.git
cd Insper-RISC-V
```

| Expected output | Common error and cause |
| :--- | :--- |
| Four submodules downloaded (`Common-Components`, `Core`, `Memory`, `Peripherals`) | Empty submodule folders, from a clone without `--recurse-submodules`. Run `git submodule update --init --recursive` |

### 2.2. Tools

The `riscv-tools` commands, `ghdl`, GCC with picolibc and Spike come from the `dev_tools` image of Infra. To run a command inside it:

```bash
docker run --rm -v "$PWD":/w -w /w ghcr.io/insper-riscv/dev_tools:latest <comando>
```

The commands of the following chapters that start with `riscv-tools`, `make` or `ghdl` run this way, or in the shell of a container of the same image. If the container runs as a user other than the owner of the clone, add `--user "$(id -u):$(id -g)"`, and `-e HOME=/w/.home` when the tool needs to write to the home directory.

### 2.3. Initial state

```bash
make all
```

| Expected output | Common error and cause |
| :--- | :--- |
| `paths OK`, `tree OK`, the tops of all platforms elaborate, the tests pass and `formal: all expectations met` | `ghdl: command not found`, from running outside the image |

### 2.4. Quartus (board only)

For a Cyclone V FPGA platform, install Quartus Prime Lite on the host and leave `quartus_sh`, `quartus_pgm` and `jtagconfig` in the `PATH`. Chapter 10 uses them.

## 3. Create the platform folder

### 3.1. Copy the model

```bash
cp -r src/simulation/template src/simulation/exemplo
```

### 3.2. Rename

The files that carry the platform name go from `template_*` to `exemplo_*`, and the word `template` inside the files becomes `exemplo`.

```bash
cd src/simulation/exemplo
mv rtl/template_map_pkg.vhd rtl/exemplo_map_pkg.vhd
mv rtl/template_sim_top.vhd rtl/exemplo_sim_top.vhd
grep -rl template . | xargs sed -i 's/template/exemplo/g'
cd ../../..
```

| Expected output | Common error and cause |
| :--- | :--- |
| `grep -r template src/simulation/exemplo` finds nothing | `check-vhdl-style` complaining that an entity name differs from the file, from forgetting to rename one of the two files in `rtl/` |

## 4. Describe the platform in `platform.yaml`

The `platform.yaml` is the only source of the map. Nothing of the map is written by hand in another file.

### 4.1. Fields

| Field | What it defines |
| :--- | :--- |
| `platform` | Platform name |
| `profile` | Core profile, in the format `rv32i` or `rv32e` followed by the extensions (`rv32im`, `rv32im_zicsr`) |
| `profiles` | Path of `Core/profiles/matrix.yaml`, the profile specification |
| `regions` | Each region with `name`, `base`, `size` (integer with suffix `K`, `M` or a sum, such as `1M-4K`), `kind` (`rom` or `ram`) and `exec` |
| `reserved` | The three words at the top of the RAM, `stdout`, `tohost` and `fromhost`, which must fit inside the RAM region |
| `boot` | `entry`, the address of the ROM `_start`, and `wait_restart`, the fixed address of the wait routine |
| `peripherals` | Each peripheral with `name`, `base` and `id` (address bits 30:28) |
| `generate` | The files to write and the parameters of the VHDL package |
| `config` | What the `config.yaml` reads from the map |
| `checks` | Where the hand-written copies that `check-memory-map` checks live |

The complete table, with the fields of the board platforms, is in chapter 14.

### 4.2. Edit

For the example, the RAM goes to 64 KiB and the profile to `rv32im`. The RAM starts at `0x8000`, so it ends at `0x18000`, and the reserved words move down with it.

```yaml
platform: exemplo
profile: rv32im
regions:
  - {name: BOOT_MEMORY, base: 0x00000000, size: 4K,  kind: rom, exec: true}
  - {name: ROM,      base: 0x00001000, size: 28K, kind: rom, exec: true}
  - {name: RAM,      base: 0x00008000, size: 64K, kind: ram}
reserved:
  stdout:   {base: 0x00017BE0, size: 1K+8}
  tohost:   {base: 0x00017FE8, size: 8}
  fromhost: {base: 0x00017FF0, size: 8}
```

The `generate` lines say `src/simulation/template/...`, and the renaming of step 3.2 already took them to `exemplo`.

### 4.3. Generate and check

```bash
riscv-tools --root . generate-memory-map --platform src/simulation/exemplo/platform.yaml
riscv-tools --root . check-memory-map --platform src/simulation/exemplo/platform.yaml
```

| Expected output | Common error and cause |
| :--- | :--- |
| Four `generated:` lines (specs, `boot_memory.ld`, `memory_map.h`, VHDL package) and `memory map OK` | `reserved stdout ... is not inside a RAM region`, because the reserved addresses ended up outside the RAM after changing the size |
| `HAS_M` true and `RAM_END_KIB` equal to 96 in the generated package | `profile` with a name that is not in `matrix.yaml` |

When the map changes, run the first command again. With `--check` at the end, the same command writes nothing and fails if any generated file is out of date.

### 4.4. Register in the repository

Every new versioned file enters the lists of the repository, and `make paths` fails while one of them is incomplete. The commands below copy, for the new platform, what the model platform has in each list.

The `paths.yaml` gets the lines of the platform and its `platform.yaml` in the list of platforms.

```bash
awk '/^  - \{name: template /{l=$0; gsub(/template/,"exemplo",l); b=b l "\n"; last=NR} {a[NR]=$0} END{for(i=1;i<=NR;i++){print a[i]; if(i==last) printf "%s", b}}' paths.yaml > paths.novo
mv paths.novo paths.yaml
sed -i 's#src/simulation/template/platform.yaml\]}#src/simulation/template/platform.yaml, src/simulation/exemplo/platform.yaml]}#' paths.yaml
```

The integration test of the top is a copy of the one of the model platform, with its images, and enters `tests/python/tests.json`.

```bash
cp tests/python/gen_template_images.py tests/python/gen_exemplo_images.py
cp tests/python/unittests/rtl/template_sim_top.py tests/python/unittests/rtl/exemplo_sim_top.py
sed -i 's/template/exemplo/g' tests/python/gen_exemplo_images.py
mkdir -p tests/python/unittests/rtl/data/exemplo
PYTHONPATH=. /opt/riscv-tools/riscv-tools/bin/python tests/python/gen_exemplo_images.py
python3 - <<'EOF'
import json
caminho = "tests/python/tests.json"
dados = json.load(open(caminho))
dados["ExemploSimTop"] = json.loads(json.dumps(dados["TemplateSimTop"]).replace("template", "exemplo"))
json.dump(dados, open(caminho, "w"), indent=4)
open(caminho, "a").write("\n")
EOF
```

The test reads the RAM base in `RAM_BASE`, at the start of `exemplo_sim_top.py`, and this value changes together with the RAM region of the `platform.yaml`.

`paths.yaml` still has to declare the top and the map package as components (`provides`), which is where `make generate-sources` takes the source list of `config.yaml` and `tests.json` from.

```bash
python3 - <<'EOF2'
texto = open("paths.yaml").read()
inicio = texto.index("  template_map:")
fim = texto.index("\n", texto.index("template_sim_top.vhd", inicio))
bloco = texto[inicio:fim]
texto = texto[:fim] + "\n" + bloco.replace("template", "exemplo") + texto[fim:]
open("paths.yaml", "w").write(texto)
EOF2
```

`scripts/generate_sources.py` and `scripts/check_top_generics.py` gain one line each, next to those of `template`.

```bash
sed -i 's#^    Saida("src/simulation/template/config.yaml", ("template_sim_top",)),#&\n    Saida("src/simulation/exemplo/config.yaml", ("exemplo_sim_top",)),#' scripts/generate_sources.py
sed -i 's#^    Saida(TESTS_JSON, ("template_sim_top",), "TemplateSimTop"),#&\n    Saida(TESTS_JSON, ("exemplo_sim_top",), "ExemploSimTop"),#' scripts/generate_sources.py
sed -i 's#^    "src/simulation/template/rtl/template_map_pkg.vhd": \[#    "src/simulation/exemplo/rtl/exemplo_map_pkg.vhd": [\n        "src/simulation/exemplo/rtl/exemplo_sim_top.vhd",\n    ],\n&#' scripts/check_top_generics.py
```

The `Makefile` gets a variable and a copy of every line that mentions the model platform.

```bash
sed -i 's#^PT := src/simulation/template$#&\nPX := src/simulation/exemplo#' Makefile
sed -i -E 's#^(\t.*)\$\(PT\)(.*)$#\1$(PT)\2\n\1$(PX)\2#' Makefile
python3 - <<'EOF2'
texto = open("Makefile").read()
linhas = [l for l in texto.split("\n") if "template" in l and l.startswith("\t@")]
texto = texto.replace(linhas[-1], linhas[-1] + "\n" + "\n".join(l.replace("template", "exemplo") for l in linhas), 1)
open("Makefile", "w").write(texto)
EOF2
```

The documentation gets one document per language and the row in the table of the `README.md` of the folder.

```bash
for l in pt-br en; do
    sed 's/template/exemplo/g' docs/$l/platform/template.md > docs/$l/platform/exemplo.md
    sed -i '/^| \[template\]/{p;s/template/exemplo/g}' docs/$l/platform/README.md
done
```

Generate the source lists and check.

```bash
make generate-sources
make paths
make memory-map
```

| Expected output | Common error and cause |
| :--- | :--- |
| `paths OK` and `tree OK`, and the `memory-map` platforms with `generated files OK` | `missing docs/pt-br/platform/exemplo.md`, from a missing platform document in one of the languages |
| | `entity-coverage exemplo_sim_top ... has no entry in tests/python/tests.json`, from a missing `ExemploSimTop` entry |

## 5. Choose the Core profile

### 5.1. The profile rule

The name of a profile is the base followed by the extensions in the order of `Core/profiles/matrix.yaml`, joined by `_`.

| Part | Values |
| :--- | :--- |
| Base | `rv32i` (32 registers) or `rv32e` (16) |
| Extensions, in this order | `zicclsm`, `zicsr`, `zicntr`, `zihpm`, `zifencei`, `zmmul`, `m` |

`zicntr` and `zihpm` imply `zicsr`, so the name never cites `zicsr` next to them; `m` implies `zmmul`, and `m` and `zmmul` do not appear together. All other combinations are valid, which gives 60 profiles per base and 120 in total. To list them:

```bash
riscv-tools profiles --spec Core/profiles/matrix.yaml --format names
```

### 5.2. Extensions outside the matrix

The extensions `Zimop`, `Zicond`, `Zihintntl` and `Zihintpause` are not part of the profile name. The platform turns them on in the `extras` field of the `platform.yaml` (`extras: [Zimop, Zicond]`), and the generated package carries `HAS_ZIMOP` and `HAS_ZICOND` true.

### 5.3. How the top passes the profile to the `core`

`generate-memory-map` writes one `HAS_*` constant per extension in the package (`HAS_E`, `HAS_M`, `HAS_ZICSR` and the others). The top exposes them as `has_*` generics of the same name, with the constant as default value, and connects them to the generics of the `core` (step 6.3). The value comes from the `profile` of the `platform.yaml`.

To run the same platform over another profile without editing it, pass the global option `--profile`.

```bash
riscv-tools --root . --profile rv32im_zicsr generate-memory-map --platform src/simulation/exemplo/platform.yaml
```

### 5.4. A profile that does not exist

If no profile fits, the new extension enters `Core/profiles/matrix.yaml` as a pull request in the `Core` repository, with the extension folder in `Core/src/<extension>/`. The contribution guide of the `Core` describes the path. After that, the submodule pointer in this repository advances and the new profile holds in every platform.

## 6. Write the top

### 6.1. Structure of `<platform>_sim_top.vhd`

The simulation top of the model platform has six blocks, which the example keeps.

| Instance | Entity | Origin |
| :--- | :--- | :--- |
| `u_clock` | `clk_gen_3way` | `src/simulation/internal-mem/rtl/` |
| `u_core` | `core` | `Core/src/core/` |
| `u_boot_memory` | `rom_simulation` | `Memory/src/ROM/SoC/` |
| `u_rom` | `rom_simulation` (two ports) | `Memory/src/ROM/SoC/` |
| `u_ram` | `ram_simulation` | `Memory/src/RAM/SoC/` |
| `u_uart` (optional) | `jtag_uart` | `Peripherals/src/UART/jtag/` |

The core has three memory outputs: the instruction fetch (BOOT_MEMORY and ROM), the data port of the ROM and the RAM, and the external bus, through which the peripherals pass.

### 6.2. Size generics

The memory sizes are power-of-two generics whose default value comes from the generated package (`BOOT_MEMORY_SIZE_BYTES`, `ROM_STORAGE_BYTES`, `RAM_STORAGE_BYTES`). No size is written in the top.

### 6.3. Profile and map in the `core`

The top declares one `has_*` generic per extension (`has_e`, `has_m`, `has_zmmul`, `has_zicsr`, `has_zicntr`, `has_zihpm`, `has_zimop`, `has_zicond`, `has_zihintntl`, `has_zihintpause`, `has_zifencei`, `has_zicclsm` and `has_interrupts`), each with the `HAS_*` constant of the package as default value. In the `generic map` of the `core`, each `has_*` of the core receives the generic of the same name of the top, and the `has_interrupts` of the core receives `has_interrupts and has_zicsr`. The region limits (`rom_end_kib`, `ram_base_kib`, `ram_end_kib`, `ext_base_kib`, `periph_base_kib`) receive the constants of the same name of the package. If the profile of step 4.2 turns on `M`, `has_m` already arrives true, and nothing else changes in the top.

`riscv-tools` passes the simulator one `-g has_*` per extension of the profile. Every top it simulates must declare the thirteen generics, and a top that does not declare one of them fails at elaboration with `cannot find in top entity generic`.

### 6.4. Window of each peripheral

The external bus of the core delivers to the top the address, the write data and the read and write enables. The UART answers when the four highest address bits are those of `UART_BASE`, which comes from the package, and the read data returns to the core in the cycle after the request. For a new peripheral, repeat the pattern: a selector by address, the enables filtered by the selector, the read data registered. For several peripherals on a board platform, use the `ext_interconnect` interconnect of `src/interconnect/`, which separates the SDRAM from the peripheral window and hands the word offset to each one (`de0-cv_top.vhd` shows the usage).

### 6.5. Interrupts

The core receives the machine interrupts through three level ports, `i_irq_software`, `i_irq_timer` and `i_irq_external`, all with default value `'0'`. They only have effect with the `has_interrupts` generic true and `has_zicsr` on, and then `mip` mirrors the three ports and `mie` masks them. The CLINT (`Peripherals/src/CLINT/soc/`) delivers `o_irq_timer` and `o_irq_software`, and the PLIC (`Peripherals/src/PLIC/soc/`) gathers the peripheral lines into `o_meip`. Each one is an ordinary peripheral, with its own window (step 6.4), and its outputs connect directly to the ports of the core.

### 6.6. CONTRIBUTING conventions

| Rule | Application in the top |
| :--- | :--- |
| Ports `i_` and `o_` | `i_clk`, `i_rst`, `o_uart_tdo` |
| Labels `u_` | `u_core`, `u_ram` |
| 72-column header | `-- ====` block at the start of the file, in Portuguese |
| Docstring per declaration | A comment in Portuguese above each generic, port, signal and constant |
| Direct instantiation | `u_x : entity work.name`, with no `component` |

### 6.7. Check

```bash
riscv-tools --root . check-vhdl-style
```

| Expected output | Common error and cause |
| :--- | :--- |
| `vhdl style OK` | A declaration without the comment above it, or a port without a prefix |

### 6.8. Elaborate

```bash
mkdir -p build/exemplo
ghdl -a --std=08 --workdir=build/exemplo $(riscv-tools vhdl-sort \
    $(find Common-Components/src Core/src -name '*.vhd' -not -path 'Core/src/common/*') \
    Memory/src/RAM/SoC/ram_simulation.vhd Memory/src/ROM/SoC/rom_simulation.vhd \
    Peripherals/src/UART/jtag/jtag_uart.vhd \
    src/simulation/internal-mem/rtl/clk_gen_3way.vhd \
    src/simulation/exemplo/rtl/*.vhd)
ghdl -e --std=08 --workdir=build/exemplo exemplo_sim_top
```

| Expected output | Common error and cause |
| :--- | :--- |
| No error message | `unit "..." not found`, from a file missing in the list or the list out of order (`vhdl-sort` sorts it) |

`make check-tops` does the same for all platforms registered in step 4.4.

## 7. Runtime

The runtime is what the program finds on start and on exit. The four hand-written files come from the model, and the map reaches them through the three files generated in chapter 4.

### 7.1. The files

| File | What it does | What changes with the map |
| :--- | :--- | :--- |
| `runtime/boot_memory.S` | `_reset` clears `stdout`, `tohost` and `fromhost` and jumps to `RV32_BOOT_ENTRY`; `rv32_wait_restart` waits for `fromhost` | Nothing, it reads the addresses from `memory_map.h` |
| `runtime/boot_memory.ld` | BOOT_MEMORY linker script, with `rv32_wait_restart` at `0x100` | Generated |
| `runtime/rv32im-fpga.specs` | Linker parameters (`__flash`, `__flash_size`, `__ram`, `__ram_size`) and the crt0 of picolibc | Generated |
| `runtime/memory_map.h` | Addresses of RAM, `tohost`, `fromhost`, `stdout`, boot entry and the base of each peripheral | Generated |
| `runtime/_exit.c` | Writes the result to `tohost` and enters `rv32_wait_restart` | Nothing |
| `runtime/stdio.c` | Takes `printf` and `putchar` to the `stdout` buffer in the RAM | Nothing |
| `runtime/spike_exit.S` | The same program end for the Spike ELF | Nothing |

### 7.2. How `tohost` ends a program

| Value written to `tohost` | Meaning |
| :--- | :--- |
| `1` | Program passed (`main` returned 0) |
| `(code << 1) \| 1` | Program failed with the given code |
| `0` | Not finished yet |

The testbench watches the writes on the RAM bus, and the first non-zero write at the `tohost` address ends the simulation with the result.

### 7.3. Check

```bash
make memory-map
```

| Expected output | Common error and cause |
| :--- | :--- |
| `memory map OK` and `generated files OK` | `generated files are out of date`, from editing the `platform.yaml` without running `generate-memory-map` again |

## 8. Simulation top and first program

### 8.1. The `config.yaml`

It gathers, for `riscv-tools`, what belongs to the platform. No address or memory size lives in it, because the `memory_map: platform.yaml` key reads them from the map.

| Section | Content |
| :--- | :--- |
| `toolchain` | GCC, `objcopy` and the `rv32im-fpga.specs` of the platform |
| `memory_map` | The `platform.yaml`, where the bases, `tohost`, `fromhost` and the profile come from |
| `paths` | Runtime sources (`_exit.c`, `stdio.c`), `boot_memory.S` and `boot_memory.ld` |
| `sim.toplevel` | `exemplo_sim_top` |
| `sim.vhdl_sources` | All sources, in dependency order, written by `make generate-sources` |
| `sim.test_module`, `sim.python_path` | The cocotb testbench, `testbench.test_c_program` of the `internal-mem` platform |
| `sim.parameters` | `BOOT_MEMORY_FILE` and `ROM_FILE` with the images of each program |
| `emulator.sources` | `spike_exit.S` |

The `sim.vhdl_sources` list is not edited by hand. It comes from the component of the top in the `provides` of the platform `paths.yaml`, which declares the components the top requires, and `make generate-sources` writes it in analysis order. If the top gains a peripheral, its component enters the `requires` of the top and the list is regenerated.

The sources of the core, in dependency order, come from:

```bash
riscv-tools --root . sources Core/core
```

### 8.2. The testbench

The `testbench/test_c_program.py` of `internal-mem` runs the clock, releases the reset, watches the writes on the RAM bus (`ram_addr`, `ram_wren`, `ram_en`, `ram_wdata`, `ram_byteena`) and stops at `tohost`. The `tohost` address reaches it through the environment, coming from the `platform.yaml`. Any top that exposes these signals with these names reuses it, and the one of the example exposes them.

### 8.3. The first program

The programs live in the `Tests` repository (`asm/` and `c/`). `Tests` carries `Insper-RISC-V` as a submodule and extends the configuration of each platform through a generated file.

First, the platform must be in a commit of the clone, and the submodule of `Tests` starts pointing to it.

```bash
git add src/simulation/exemplo paths.yaml Makefile tests docs scripts
git commit -m "feat: plataforma exemplo"
cd ..
git clone --recurse-submodules git@github.com:insper-riscv/Tests.git
cd Tests
git -C Insper-RISC-V fetch ../../Insper-RISC-V HEAD
git -C Insper-RISC-V checkout FETCH_HEAD
git -C Insper-RISC-V submodule update --init --recursive
```

The `Tests` clone sits next to the `Insper-RISC-V` one, in `../Tests`, which is where `check-memory-map` looks for it. Then `platform sync` writes the platform configuration already resolved against the `platform.yaml`, with the paths preceded by the submodule folder.

```bash
riscv-tools platform sync --prefix Insper-RISC-V \
    --source Insper-RISC-V/src/simulation/exemplo/config.yaml \
    --output tools/riscv_build/config.platform-exemplo.yaml
```

| Expected output | Common error and cause |
| :--- | :--- |
| `platform synced: tools/riscv_build/config.platform-exemplo.yaml` | `No such file` at `Insper-RISC-V/src/simulation/exemplo`, because the submodule still points to a commit without the platform |

The programs include a header with the map, chosen by the `include_dir` of the configuration. Each platform has its own headers folder, copied from `include/` with the three addresses replaced by those of the `platform.yaml`.

```bash
mkdir tools/riscv_build/include-exemplo
sed -e 's/0x00030000/0x00018000/' -e 's/0x0002FBE0/0x00017BE0/' -e 's/0x0002FFE8/0x00017FE8/' \
    tools/riscv_build/include/rv32_platform.h > tools/riscv_build/include-exemplo/rv32_platform.h
echo "tools/riscv_build/include-exemplo/rv32_test.h" >> .gitignore
```

| Address | Value in the example | Origin in the `platform.yaml` |
| :--- | :--- | :--- |
| `RV32_RAM_END` | `0x00018000` | End of the `RAM` region |
| `RV32_STDOUT_BASE` | `0x00017BE0` | `reserved.stdout.base` |
| `RV32_TOHOST` | `0x00017FE8` | `reserved.tohost.base` |

For `check-memory-map` to check this copy, replace `checks: []` at the end of the `platform.yaml` of the example with the three lines below.

```yaml
checks:
  - {name: Tests header RV32_RAM_BASE, file: ../Tests/tools/riscv_build/include-exemplo/rv32_platform.h, optional: true, pattern: '#define RV32_RAM_BASE\s+(0x[0-9A-Fa-f]+)', expect: RAM.base}
  - {name: Tests header RV32_RAM_END, file: ../Tests/tools/riscv_build/include-exemplo/rv32_platform.h, optional: true, pattern: '#define RV32_RAM_END\s+(0x[0-9A-Fa-f]+)', expect: RAM.end}
  - {name: Tests header RV32_STDOUT_BASE, file: ../Tests/tools/riscv_build/include-exemplo/rv32_platform.h, optional: true, pattern: '#define RV32_STDOUT_BASE\s+(0x[0-9A-Fa-f]+)', expect: stdout.base}
```

Create `tools/riscv_build/config.exemplo.yaml` with the content below.

```yaml
extends: config.platform-exemplo.yaml
paths:
  include_dir: tools/riscv_build/include-exemplo
  build_dir: build-exemplo
  c_dir: c
  asm_dir: asm
```

Finally, generate the header of the C programs, then compile and simulate one program from `asm/` and two from `c/`.

```bash
riscv-tools --config tools/riscv_build/config.exemplo.yaml generate-header
riscv-tools --config tools/riscv_build/config.exemplo.yaml compile --emit hex --only arithmetic-add,multiply,stdout-printf
riscv-tools --config tools/riscv_build/config.exemplo.yaml sim
```

| Expected output | Common error and cause |
| :--- | :--- |
| `arithmetic-add: PASS`, `multiply: PASS` and `stdout-printf: PASS`, with the label `(rv32im)` on the last two | `timed out after ... cycles without a result`, when `rv32_platform.h` kept the addresses of another platform and the program writes `tohost` where the testbench does not look |
| `compile` generates `manifest.json` with the programs | `cannot find in top entity generic 'has_interrupts'`, when the top does not declare the `has_*` generics of step 6.3 (the name changes with the missing generic) |
| | `rv32_test.h: No such file or directory`, from skipping `generate-header` |
| | `region ... overflowed` at link time, when the program does not fit in the 28 KiB ROM |

Inside `Insper-RISC-V`, `make test TEST=ExemploSimTop` runs the integration test of the top registered in step 4.4, without the test project.

## 9. Certification

### 9.1. What is certified

The ACT4 suite certifies a core profile, not a memory map. The `Certification` repository runs each of the 120 profiles of `Core/profiles/matrix.yaml` on the modular simulation platform (`src/simulation/modular`), with 1 MB of ROM and RAM. A profile without `Zifencei` runs with the memories inside the chip, and a profile with `Zifencei` runs with the ROM and the RAM behind the 4 kbit caches. The target of each profile (UDB, Sail configuration, `test_config.yaml`) and the `config.profile-<profile>.yaml` or `config.flash-<profile>.yaml` are already in the repository, generated by `tools/riscv_build/gen_profiles.py` and `gen_flash_profiles.py` from the profile matrix of the submodule.

For the new platform, the certification holds for the profile it chooses in step 4.2. Its memory map is proved by the program of step 8.3.

### 9.2. Run the chosen profile

The tools come from the `ci-act4` image of Infra. The run uses about 15 GiB of memory per profile and needs a writable home directory.

```bash
git clone --recurse-submodules git@github.com:insper-riscv/Certification.git
cd Certification
docker run --rm --memory=22g --ulimit stack=-1 -e HOME=/w/.home --user "$(id -u):$(id -g)" \
    -v "$PWD":/w -w /w ghcr.io/insper-riscv/ci-act4:latest \
    riscv-tools --config tools/riscv_build/config.profile-rv32im.yaml certify
```

For a profile with `Zifencei`, use `config.flash-<profile>.yaml` in place of `config.profile-<profile>.yaml`. To restrict to the extensions of the profile, add `--extensions I,M` to `certify`.

| Expected output | Common error and cause |
| :--- | :--- |
| One `PASS` line per test of the profile (51 in `rv32im`) and `=== Summary ===` with no `FAIL` line; the log is in `logs/certification/latest.log` | `Permission denied @ dir_s_mkdir - /.local`, because the container runs as another user and the home directory is not writable. Pass `-e HOME=<writable folder>` |
| | `profile ... not found`, because the profile of the platform is not in `matrix.yaml` |
| | Failure of `Zifencei-fence.i`, when the test that rewrites its own code runs from the ROM, which ignores stores. The `flash-ram-*` target uses the variant with the test body in the RAM |

### 9.3. Profile without a target

A new profile of the Core matrix gets its target by running the generators in the `Certification` repository.

```bash
uv run python tools/riscv_build/gen_profiles.py
uv run python tools/riscv_build/gen_flash_profiles.py
```

## 10. Board

This chapter applies only if the platform has an FPGA. The Quartus project of a board platform is neither written nor copied by hand: `riscv-tools board generate` writes it from the `platform.yaml` of the platform and from the board package in `boards/<board>/`. The complete step by step, from the board package to running programs, is in [adicionar-placa.md](adicionar-placa.md), and this chapter shows only what a new platform does in it.

### 10.1. Declare the board in `platform.yaml`

The new platform starts from a copy of the nearest board platform (`src/cyclone-v/de0-cv` for the full profile, `src/cyclone-iv-e/de0-nano` for a reduced profile). In `platform.yaml`, the `board` field (or the `boards` list) chooses the board, the `clocks` and `io` fields say what the SoC asks for, and each external region chooses its backend. Step 6 of [adicionar-placa.md](adicionar-placa.md) describes the fields, and step 7 the validator that compares the request with what the board offers.

### 10.2. Generate and check the project

```bash
riscv-tools --root . generate-memory-map --platform src/<family>/<platform>/platform.yaml
riscv-tools --root . --board <board> board generate --platform src/<family>/<platform>/platform.yaml --out build
riscv-tools --root . --board <board> board generate --platform src/<family>/<platform>/platform.yaml --out build --check
```

`board generate` writes the board top, the PLL, the `.qpf`, the `.qsf`, the `.sdc` and the `capacity.json` into `build/<platform>-<board>/`, and the `build` folder is not versioned. The files written and what each contains are in [../boards/geracao.md](../boards/geracao.md). A fit or pin error comes out of the validator before any compilation.

| Expected output | Common error and cause |
| :--- | :--- |
| The project files in `build/<platform>-<board>/` and `--check` with no difference | `profile does not fit` (V11 or V12), from a profile larger than the device; the fix is to reduce the profile, the caches or the emulated memory |

### 10.3. Register the platform in the repository

The platform enters `paths.yaml`, the `Makefile` lists that run `generate` and `generate-check`, and `scripts/generate_sources.py`, as in step 4.4. Then check.

```bash
make generate-sources
make paths
make memory-map
```

### 10.4. Compile, program and run programs

Compiling up to `map` (N0) and up to `sta` (N1), programming (N2) and the programs of the Tests repository (N3) follow chapter 10 of [adicionar-placa.md](adicionar-placa.md), with the board lock and the warning about compiling and programming in the same shell in [placa.md](placa.md). `riscv-tools platform sync` writes, in the `Tests` clone, the configuration derived from the `config.yaml` of the platform, as in step 8.3.

### 10.5. Timing report

After compilation, the Timing Analyzer report is in `output_files/` of the generated project. To list the critical paths of each domain, run `timing-paths` with the `config.yaml` of the platform and the project already compiled.

```bash
riscv-tools --config src/<family>/<platform>/config.yaml timing-paths --npaths 2
```

| Expected output | Common error and cause |
| :--- | :--- |
| A Markdown table with one path per row: clock, source, destination, width, slack and delay | `quartus_sta failed` with `Fitter (quartus_fit) failed or was not run`, from running before the full compilation |

A negative setup slack means a path longer than the clock period, and the result changes from seed to seed.

### 10.6. New board

A board the repository does not know yet starts from the board package (`boards/<board>/`), not from a copy of a platform. The step by step, from `board.yaml` to level N2, is in [adicionar-placa.md](adicionar-placa.md).

## 11. Add a new peripheral

The example is an LED register, `led_register`, with a 32-bit register whose low bits light the LEDs. A peripheral has a `soc` side, family independent, and, when it needs an FPGA shell, a `<family>` side. The steps below apply in the `Peripherals` repository, in `Insper-RISC-V/Peripherals` or in your own clone.

### 11.1. Folder and entity

The peripheral lives in `Peripherals/src/<PERIPHERAL>/soc/`. The folder takes the name of what the peripheral is, in lowercase with hyphens, or in capitals when the name is an acronym that the `identifier_folders` of the repository `paths.yaml` lists.

```bash
mkdir -p Peripherals/src/LED/soc
```

The `Peripherals/src/LED/soc/led_register.vhd` follows the common peripheral bus (`i_clk`, `i_rst`, `i_data_in`, `i_address`, `i_write`, `i_read`, `o_data_out`) and the style guide of the repository.

```vhdl
-- ============================================================================
-- Registrador de LEDs
-- ============================================================================
-- Periférico mapeado em memória com um único registrador de 32 bits, cujos
-- bits menos significativos acendem os LEDs da placa. A escrita no endereço 0
-- carrega o registrador no próximo clock; a leitura devolve o valor guardado
-- e não tem efeito colateral. Endereços diferentes de 0 leem zero e ignoram
-- a escrita.
-- ============================================================================

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity led_register is
    generic(
        -- Número de LEDs ligados aos bits menos significativos do registrador
        led_count : positive := 10
    );
    port(
        -- Clock do módulo
        i_clk      : in  std_logic;
        -- Reset síncrono, ativo em '1'
        i_rst      : in  std_logic;
        -- Dado de escrita vindo do processador
        i_data_in  : in  std_logic_vector(31 downto 0);
        -- Endereço de palavra dentro do periférico
        i_address  : in  std_logic_vector(3 downto 0);
        -- Pulso de escrita do processador ('1' = escreve)
        i_write    : in  std_logic;
        -- Pulso de leitura do processador (sem efeito colateral)
        i_read     : in  std_logic;
        -- Dado de leitura para o processador
        o_data_out : out std_logic_vector(31 downto 0);
        -- Saída para os LEDs, ativa em '1'
        o_leds     : out std_logic_vector(led_count - 1 downto 0)
    );
end entity led_register;

architecture rtl of led_register is

    -- Valor guardado dos LEDs
    signal leds_reg : std_logic_vector(led_count - 1 downto 0);
    -- Endereço de palavra do registrador
    constant ADDR_LEDS : std_logic_vector(3 downto 0) := "0000";

begin

    p_write : process(i_clk)
    begin
        if rising_edge(i_clk) then
            if i_rst = '1' then
                leds_reg <= (others => '0');
            elsif i_write = '1' and i_address = ADDR_LEDS then
                leds_reg <= i_data_in(led_count - 1 downto 0);
            end if;
        end if;
    end process p_write;

    o_data_out <= std_logic_vector(resize(unsigned(leds_reg), 32))
                  when i_address = ADDR_LEDS else (others => '0');
    o_leds     <= leds_reg;

end architecture rtl;
```

### 11.2. Entity test

Every peripheral has a cocotb test in `Peripherals/tests/python/unittests/<PERIPHERAL>/`, with an `__init__.py`, and a protocol that describes the peripheral signals in `tests/python/utils/dut.py`.

```bash
mkdir -p Peripherals/tests/python/unittests/LED
echo '"""Package LED of the peripheral tests."""' > Peripherals/tests/python/unittests/LED/__init__.py
```

Add at the end of `tests/python/utils/dut.py`:

```python
class LedDut(BusDut, Protocol):
    """Signals of the LED register."""

    o_leds: LogicArrayObject
```

The test `unittests/LED/led_register.py` uses the bus helpers of `tests/python/utils/bus.py`.

```python
"""LED_REGISTER: a escrita carrega os LEDs e a leitura devolve o valor."""

import cocotb

from tests.python.utils import bus
from tests.python.utils.check import check
from tests.python.utils.dut import LedDut

LEDS_ADDR = 0
OTHER_ADDR = 1
PATTERN = 0x2A5


@cocotb.test()
async def test_write_then_read(dut: LedDut) -> None:
    """Depois do reset os LEDs estão apagados, e a escrita os acende."""
    await bus.reset(dut)
    check(int(dut.o_leds.value) == 0, "LEDs apagados depois do reset")
    await bus.write(dut, LEDS_ADDR, PATTERN)
    check(int(dut.o_leds.value) == PATTERN, "LEDs acesos com o padrão")
    check(await bus.read(dut, LEDS_ADDR) == PATTERN, "leitura devolve o valor")
    check(await bus.read(dut, OTHER_ADDR) == 0, "outro endereço lê zero")
```

### 11.3. Manifest

The test enters the `tests/python/tests.json` catalog, with the top entity, the sources and the test module.

```json
"LedRegister": {
    "toplevel": "led_register",
    "sources": ["src/LED/soc/led_register.vhd"],
    "test_module": "tests.python.unittests.LED.led_register",
    "build_args": ["--std=08"],
    "test_args": ["--std=08"]
}
```

The `paths.yaml` of the repository gets the peripheral folder in `entry points`, the pair of documents of step 11.4 and, when the folder is in capitals, its name in `tree.identifier_folders`.

### 11.4. Document

Each peripheral has one document per language, `docs/pt-br/<PERIPHERAL>/led_register.md` and `docs/en/<PERIPHERAL>/led_register.md`, with the language selector, the numbered sections and the license footer. The `README.md` and `README.en.md` of the repository get the peripheral line in the structure tables.

### 11.5. Check

```bash
make check
make paths
make test TEST=LedRegister
riscv-tools --root . check-vhdl-style
```

| Expected output | Common error and cause |
| :--- | :--- |
| `VHDL syntax check passed`, `tree OK`, `TESTS=1 PASS=1` and `vhdl style OK` | `TREE folder-names src/LED: use lowercase letters...`, from `LED` missing in `tree.identifier_folders` of the `paths.yaml` |
| | `entity-coverage ... has no entry in tests/python/tests.json`, from a missing manifest of step 11.3 |

### 11.6. Window in the `platform.yaml` and in the top

A platform repository uses the peripheral after the `Peripherals` submodule pointer advances to the commit that carries it. The window enters the `platform.yaml` of the platform.

```yaml
peripherals:
  - {name: UART, offset: 0x40000000, id: 4, size: 1K, padding: 0x0FFFFC00}
  - {name: LED,  offset: 0x50000000, id: 5, size: 1K, padding: 0x0FFFFC00}
```

After `generate-memory-map`, the package gains `LED_BASE` and `LED_ID`, and `memory_map.h` gains `RV32_LED_BASE`. In the top, the window selector, the filtered enables and the read data follow the pattern of step 6.4, and the source `led_register.vhd` enters the `sim.vhdl_sources` list of the `config.yaml`, the `Makefile` of the platform and the `.qsf`, if there is a board.

## 12. Add a new memory type

The path is that of chapter 11, in the `Memory` repository. The example is a scratch RAM, `scratchpad_ram`, a single-port memory with synchronous write and read.

### 12.1. Folder and entity

A memory lives in `Memory/src/<type>/`, with `SoC/` for what is family independent and the family folder (`Cyclone-V/`, `FPGA/`) for what uses megafunctions. The folders `SoC`, `RAM`, `ROM`, `FPGA` and `Cyclone-V` keep their capitals because they are identifiers, and the name of a new type uses lowercase.

```bash
mkdir -p Memory/src/scratchpad/SoC
```

The `Memory/src/scratchpad/SoC/scratchpad_ram.vhd` follows the same style guide.

```vhdl
-- ============================================================================
-- RAM de rascunho
-- ============================================================================
-- Memória de uma porta com escrita e leitura síncronas, de palavra inteira.
-- A leitura devolve, no ciclo seguinte ao pedido, o conteúdo do endereço
-- pedido; uma escrita e uma leitura no mesmo ciclo devolvem o valor antigo.
-- ============================================================================

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity scratchpad_ram is
    generic(
        -- Largura do endereço de palavra em bits
        addr_width : positive := 4
    );
    port(
        -- Clock da memória
        i_clk      : in  std_logic;
        -- Endereço de palavra
        i_addr     : in  std_logic_vector(addr_width - 1 downto 0);
        -- Dado de escrita
        i_data_in  : in  std_logic_vector(31 downto 0);
        -- Habilita de escrita ('1' = escreve)
        i_we       : in  std_logic;
        -- Dado lido, válido no ciclo seguinte ao pedido
        o_data_out : out std_logic_vector(31 downto 0)
    );
end entity scratchpad_ram;

architecture rtl of scratchpad_ram is

    -- Vetor de palavras da memória
    type word_array_t is array (0 to 2 ** addr_width - 1) of std_logic_vector(31 downto 0);
    -- Conteúdo da memória, zerado no início da simulação
    signal words : word_array_t := (others => (others => '0'));

begin

    p_access : process(i_clk)
    begin
        if rising_edge(i_clk) then
            o_data_out <= words(to_integer(unsigned(i_addr)));
            if i_we = '1' then
                words(to_integer(unsigned(i_addr))) <= i_data_in;
            end if;
        end if;
    end process p_access;

end architecture rtl;
```

### 12.2. Entity test

The `Memory` tests live in `tests/python/unittests/<type>/` and use `Dut` and the helpers of `tests/python/unittests/checks.py`.

```bash
mkdir -p Memory/tests/python/unittests/scratchpad
echo '"""Package scratchpad of the memory tests."""' > Memory/tests/python/unittests/scratchpad/__init__.py
```

```python
"""SCRATCHPAD_RAM: a leitura devolve o que a escrita guardou."""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer

from tests.python.unittests.checks import check_equal
from tests.python.unittests.dut import Dut

WORD = 0xCAFE_F00D
ADDR = 5


@cocotb.test()
async def test_write_then_read(dut: Dut) -> None:
    """Escreve uma palavra, lê no ciclo seguinte e confere o valor."""
    cocotb.start_soon(Clock(dut.i_clk, 10, unit="ns").start())
    dut.i_we.value = 0
    dut.i_addr.value = ADDR
    dut.i_data_in.value = WORD
    await Timer(1, unit="ns")
    dut.i_we.value = 1
    await RisingEdge(dut.i_clk)
    dut.i_we.value = 0
    await RisingEdge(dut.i_clk)
    await Timer(1, unit="ns")
    check_equal(int(dut.o_data_out.value), WORD, "palavra lida")
```

### 12.3. Manifest, document and check

The manifest is an entry of `tests/python/tests.json` like the one in step 11.3, with `toplevel` `scratchpad_ram`, the source `src/scratchpad/SoC/scratchpad_ram.vhd` and the module `tests.python.unittests.scratchpad.scratchpad_ram`. The `paths.yaml` of `Memory` gets the folder `src/scratchpad/SoC` in `entry points` and the two documents, `docs/pt-br/scratchpad/scratchpad_ram.md` and `docs/en/scratchpad/scratchpad_ram.md`, in a `design documents` line. An entity without an entity test of its own needs a justification in `tree.exceptions`, and one that has a test does not.

```bash
make check
make paths
make test TEST=ScratchpadRam
riscv-tools --root . check-vhdl-style
```

| Expected output | Common error and cause |
| :--- | :--- |
| `VHDL syntax check passed`, `tree OK`, `TESTS=1 PASS=1` and `vhdl style OK` | `entity-coverage`, from an entity with neither an entry in `tests.json` nor a justification in `tree.exceptions` |

### 12.4. Use in a platform

The top instantiates the new memory in place of one of the existing ones, as long as the interface is that of the block it replaces (rule 3 of section 5 of the CONTRIBUTING). When the region stops being internal, the `memory` field of the `platform.yaml` changes (`rom: {external: true}`, `icache: {enabled: true, size_bits: 32768}`), and the generated package carries `ROM_EXTERNAL`, `RAM_EXTERNAL` and the cache sizes.

## 13. CI and pull request

### 13.1. Check before opening

Every pull request of this repository goes through, locally:

```bash
git submodule update --init --recursive
make all
make generate-check
```

| Command | What it runs |
| :--- | :--- |
| `make paths` | The paths of `paths.yaml` and the tree shape (`check-tree --kind top`) |
| `make check` | The elaboration of the tops of all platforms and the uniqueness of entity names across repositories |
| `make unit-tests` | The memory map check and the cocotb tests of the platforms |
| `make formal` | The formal proof of the interconnect |
| `make generate-check` | The generated files of each `platform.yaml` are up to date |

### 13.2. What the CI runs

The CI runs on every push, in nine jobs, inside the `ci-vhdl` image of Infra.

| Job | What it checks |
| :--- | :--- |
| `reuse` | Reuses the result of an approved pull request of the same tree; when in doubt, runs everything |
| `vhdl-syntax` | `make paths`, `check-vhdl-style` and `make check` |
| `unit-tests` | `make unit-tests` |
| `formal - yices`, `formal - bitwuzla`, `formal - boolector`, `formal - abc-bmc3` | The formal proof, once per engine |
| `formal` | Aggregates the engines; it is the check the branch ruleset requires |
| `python-static-analysis` | `ruff`, `pycodestyle`, `pydocstyle`, `pylint`, `pyright`, `pyrefly`, `deptry`, `complexipy`, `codeclone`, `semgrep` and `uv audit` over the Python files |

A new platform enters these jobs through the lists of step 4.4: `make paths` checks its files, `make check` elaborates its top and `make unit-tests` runs its test and checks the map.

### 13.3. Open the pull request

1. If the change altered a submodule (a peripheral, a memory, a Core extension), first open and conclude the pull request in its repository, following its `CONTRIBUTING.md`. Then advance the submodule pointer in this repository.
2. Raise the version in `pyproject.toml` and the same version in the `insper-riscv` block of `uv.lock`.
3. Update `README.md`, `README.en.md` and the affected documentation, in both languages.
4. Open the pull request against `main`. The commit of a new platform carries the folder `src/<family>/<platform>/`, the `paths.yaml`, the `Makefile`, the `tests/python/tests.json`, the tests, the documents and the generated files.
5. In the test project, the configuration generated by `platform sync` (`config.platform-<platform>.yaml`), the `config.<platform>.yaml` and the headers folder enter a pull request of the `Tests` repository, after the `Insper-RISC-V` pointer advances.

In a pull request from someone outside the project, the CI only starts after a member who can merge approves the run on the pull request page.

## 14. Reference

### 14.1. Why the decisions

| Decision | Reason |
| :--- | :--- |
| `platform.yaml` as the single source | Each address and each size exists in one place only, and `check-memory-map` and `generate-memory-map --check` fail when a copy diverges, instead of the error showing up on the board |
| `soc/` folder and a folder per family | The `soc` side runs in simulation and on any FPGA; the family side keeps only what depends on a megafunction |
| `src/common/` as a submodule in Core, Memory and Peripherals | The common blocks have a single origin (`Common-Components`), and each repository builds on its own |
| The top only connects | A reusable block lives in the repository that owns it, and the platform instantiates it through the submodule |
| `has_*` generics in the top | `riscv-tools` runs the same platform over any profile by passing `-g has_*`, without editing the VHDL |
| Each module checks only what is its own | Each repository has its own tests and proofs, and this repository runs only the integration |
| Certification per profile | The ACT4 result depends on the core implementation, not on the memory map the platform chooses |

### 14.2. Fields of the `platform.yaml`

| Field | Required | Content |
| :--- | :--- | :--- |
| `platform` | Yes | Platform name |
| `profile`, `profiles` | Yes | Core profile and path of the profile matrix, relative to the `platform.yaml` |
| `regions` | Yes | `name`, `base`, `size`, `kind` (`rom` or `ram`) and `exec` of each region; every region ends at `0x80000000` or before |
| `reserved` | Yes | `stdout`, `tohost` and `fromhost`, inside the RAM region |
| `boot` | Yes | `entry` in an executable region and `wait_restart` in the first region |
| `peripherals` | Yes | `name`, `base` and `id`, with the base equal to `0x80000000 \| id << 28` |
| `flash` | No | FLASH region and the banks (`name`, `base`, `size`) that the board writes and executes |
| `memory` | No | `rom` and `ram` with `external`, `icache` and `dcache` with `enabled` and `size_bits` |
| `extras` | No | Extensions outside the matrix that the platform turns on (`Zimop`, `Zicond`, `Zihintntl`, `Zihintpause`) |
| `generate` | Yes | `specs`, `bank_specs`, `boot_ld`, `runtime`, `banks_h` and `vhdl`, each with the `path` to write |
| `config` | Yes | `rom`, `ram` and `addr_widths`, what the `config.yaml` reads from the map |
| `checks` | No | Hand-written copies to check, each with `name`, `file`, `pattern` or `yaml`, and `expect` |

### 14.3. Known errors

| Message | Cause |
| :--- | :--- |
| `reserved stdout ... is not inside a RAM region` | The reserved words ended up outside the RAM after changing the size or the base |
| `generated files are out of date` | The `platform.yaml` changed without running `generate-memory-map` |
| `cannot find in top entity generic 'has_e'` | The simulated top does not declare the thirteen `has_*` generics |
| `timed out after ... cycles without a result` | The `rv32_platform.h` header of the test project has the `tohost` of another platform, or the BOOT_MEMORY does not jump to the start of the ROM |
| `rv32_test.h: No such file or directory` | `generate-header` did not run for the platform configuration |
| `unit "..." not found` | A source is missing in the `ghdl` list, or the list is out of order |
| `missing docs/...` in `make paths` | The platform, peripheral or memory document is missing in one of the languages |
| `entity-coverage ... has no entry in tests/python/tests.json` | The entity or the top has no registered test |
| `TREE folder-names ...: use lowercase letters, digits and hyphens` | Folder with a capitalized name that is not in `tree.identifier_folders` |
| `Permission denied @ dir_s_mkdir - /.local` in `certify` | The container runs without a writable home directory; pass `-e HOME=<folder>` |
| `Can't scan JTAG chain` | The Quartus compilation and programming ran in different shells |

---

Copyright 2026 Insper. Licensed under the [Apache License, Version 2.0](../../../LICENSE).
