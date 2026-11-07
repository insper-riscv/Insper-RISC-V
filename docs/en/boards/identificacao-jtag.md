# Board identification by JTAG

## 1. Goal

`riscv-tools` discovers which board is connected to the host, picks the right board for the platform, locks it for exclusive use and programs through the right cable. The IDCODE, the cable and the lock are written in no `config.yaml`: the board data is in the `board.yaml` ([formato.md](formato.md)), and the rest comes from what the host sees. The command reference is the `board` module of the Tools.

## 2. What identifies a board

Four identity sources exist, and two are useful.

| Source | Stability | Tells two equal boards apart? | Use |
| :--- | :--- | :--- | :--- |
| FPGA IDCODE in the chain, without the 4 version bits | Fixed | No | Identifies the device and the candidate boards |
| Cable name (`USB-Blaster [1-2]`) | Changes on reconnect | Only during the session | `-c` argument of `quartus_pgm`, never a key |
| USB serial number | Fixed | No, the same value appears on several cables | Discarded |
| Stable USB port path (udev `ID_PATH`) | Fixed while the cable stays on the same port | Yes | Disambiguation key |

The board is the pair formed by the device (IDCODE) and the USB port. The IDCODE says what the board may be, and the port says which candidate it is.

## 3. Algorithm

1. `jtagconfig` lists the cables and the chain of each.
2. The name `[bus-port]` of each cable becomes the system port path, and the udev `ID_PATH` is read.
3. Each IDCODE is compared with `jtag.chain` of the `board.yaml` of every known board, which gives the candidates per cable.
4. The host inventory links the port path to a board and fixes the choice.
5. Without an inventory entry, a single candidate is the choice, and more than one is an ambiguity.

The choice among candidates never follows the listing order of `jtagconfig`.

## 4. Host inventory

The inventory is `~/.config/riscv-tools/boards.yaml`, or `/etc/riscv-tools/boards.yaml`, and the first that exists applies.

```yaml
host: ws
lock_dir: /tmp
boards:
- {id: de0-cv-ws, board: de0-cv, usb_path: "pci-0000:00:14.0-usb-0:2"}
- {id: de2-115-ws, board: de2-115, usb_path: "pci-0000:00:14.0-usb-0:3"}
```

The command `riscv-tools board scan --save` records the cables it identifies, and a cable with several candidates asks for `--assign PORT=BOARD`.

## 5. Ambiguity cases

| # | Case | Resolution |
| :--- | :--- | :--- |
| 1 | One cable, one candidate | Chosen |
| 2 | Two equal boards on the same host | The inventory breaks the tie; without it, an error with the list of cables |
| 3 | Equal boards on different hosts | Each host has its inventory, and the `id` carries the host name |
| 4 | Same IDCODE for different devices (`020F70DD` serves the 10CL120, the EP3C120 and the EP4CE115) | The candidates are all boards that cite the IDCODE |
| 5 | Same device on different boards | The inventory, or `--board`, breaks the tie |
| 6 | Revisions of the same device (`031050DD` does not separate `10M50DA` from `10M50DC`) | The board declares `device`, and the Tools warns that the IDCODE does not prove the variant |
| 7 | Unknown IDCODE | Error with the IDCODEs searched and the cables seen |
| 8 | Broken chain | Infrastructure error; only powering the board off and on solves it |
| 9 | Busy cable | The lock refuses and shows the owner; `--wait` waits |

## 6. Selection on the command line

From the strongest source to the weakest: `--cable`, `--board-id`, `--board`, the `board` field of the `platform.yaml` and `auto`.

| Form | Effect |
| :--- | :--- |
| `board: auto` | Chooses among the present and free boards of `boards` |
| `board: <name>` or `--board <name>` | Fixes the board; the chain is still checked against the `board.yaml` (rule V17) |
| `--board-id <id>` | Chooses an inventory entry |
| `--cable "<name>"` | Forces the cable and skips the inventory |

## 7. Lock per board

Each board has a lock file, taken with an exclusive `flock` for the whole session, named after the board identifier without hyphens plus the host (`de0cv-ws.lock`). The owner writes host, user, process, command and instant, and whoever finds the board busy reads that record. Without `--wait`, the lock fails at once; with `--wait`, it waits up to 4 hours.

## 8. Boards without a standard USB-Blaster

| Board | Cable | Handling |
| :--- | :--- | :--- |
| `de10-nano` | USB-Blaster II (`DE-SoC [USB-1]`), USB IDs `09fb:6010` before the firmware load and `09fb:6810` after | The chain has the HPS (`4BA00477`) and the FPGA (`02D020DD`), and the FPGA is item `@2`; `doctor` warns about the firmware not yet loaded and suggests removing the HPS from the chain in the programmer on error 209025, applying nothing |
| `de0-nano-soc` | The same as the `de10-nano` | Told apart by the FPGA IDCODE (`02D010DD`) |
| `mkr-vidor-4000` | The USB connects only to the SAMD21 (`2341:8056`) | `board scan` recognizes the board by the USB ID, and `doctor` says the `USBBlaster` sketch is missing on the SAMD21, which the tools never write |

`board scan` also lists the boards the USB shows without a readable chain. The rule reads the `jtag.usb` IDs of each package, so a new board with its own cable needs no code. The ID of the common USB-Blaster (`09fb:6001`) names no board.

## 9. Without a board

| Command | Without a connected board |
| :--- | :--- |
| `platform sync`, `board generate`, simulation and `check-*` | Work, without JTAG |
| `program --compile-only` with `board: auto` | Error with the list of compatible boards and a request for `--board`; with the board named, it compiles |
| `program`, `run` and board certification | Error `no board found`, with the IDCODEs searched |

The `board doctor` subcommand checks cable, chain, processes that use the cable and the special boards, and prints what is missing without changing anything. The `board scan`, `board select` and `board lock` subcommands are described in the `board` module of the [Tools](https://github.com/insper-riscv/Tools).

---

Copyright 2026 Insper. Licensed under the [Apache License, Version 2.0](../../../LICENSE).
