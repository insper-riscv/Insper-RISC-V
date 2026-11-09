# 28BYJ-48 stepper motor on the DE0-CV

🌐 [Português](../../pt-br/platform/stepper-motor.md) · [English](../../en/platform/stepper-motor.md)

## 1. Architecture

The `internal-mem` platform exposes a four-bit GPIO at `0x90000000`. The CPU writes the coil sequence to this peripheral, and the four pins drive the ULN2003 inputs. The FPGA neither powers nor directly drives the motor coils.

The physical UART remains at `0xC0000000` and on its existing GPIO_0 pins. Both peripherals occupy separate windows and can be used by the same program.

| Peripheral | Base | Window |
| :--- | :--- | ---: |
| Motor GPIO | `0x90000000` | 1 |
| Physical UART | `0xC0000000` | 4 |

## 2. Electrical connection

The ULN2003 receives 3.3 V logic signals from the FPGA and switches the 5 V coil supply. The board and driver grounds are connected together.

| JP2 | Board signal | FPGA pin | ULN2003 |
| ---: | :--- | :--- | :--- |
| 1 | `GPIO_1[0]` | H16 | IN1 |
| 2 | `GPIO_1[1]` | A12 | IN2 |
| 3 | `GPIO_1[2]` | H15 | IN3 |
| 4 | `GPIO_1[3]` | B12 | IN4 |
| 11 | VCC5 | supply | `+` |
| 12 | GND | ground | `-` |

GPIO_0 pins M16 and C16 remain reserved for UART reception and transmission, respectively.

Never connect VCC5 to an FPGA I/O pin. The motor connects to the ULN2003 socket, while H16, A12, H15 and B12 connect only to logic inputs IN1 through IN4. Turn the board off before changing the wiring.

## 3. Registers

The peripheral is the four-bit GPIO block. Offsets are byte addresses from `RV32_MOTOR_BASE`.

| Offset | Register | Program use |
| :--- | :--- | :--- |
| `0x00` | `DIR` | Write `0xF` to enable IN1 through IN4 as outputs |
| `0x04` | `OUT_LOAD` | Load all four signals at once |
| `0x08` | `OUT_SET` | Set the bits written as 1 |
| `0x0C` | `OUT_CLR` | Clear the bits written as 1 |
| `0x10` | `OUT_TGL` | Toggle the bits written as 1 |
| `0x24` | `PINS` | Read the pins after synchronization |

At reset, all four pins start as inputs. The program loads zero into `OUT_LOAD` before writing `0xF` to `DIR`, which prevents an old combination from being enabled when the direction changes.

## 4. Half-step sequence

Bit 0 drives IN1, and bit 3 drives IN4. Forward motion uses the sequence below; reverse motion walks through the same sequence backwards.

| Index | IN4..IN1 | Hexadecimal |
| ---: | :---: | :---: |
| 0 | `0001` | `0x1` |
| 1 | `0011` | `0x3` |
| 2 | `0010` | `0x2` |
| 3 | `0110` | `0x6` |
| 4 | `0100` | `0x4` |
| 5 | `1100` | `0xC` |
| 6 | `1000` | `0x8` |
| 7 | `1001` | `0x9` |

The `stepper-motor` program starts with a short self-test that writes and reads back all eight states. It then holds each movement state for 100,000 cycles of the 50 MHz core, equal to 2 ms. It performs 1024 half steps in each direction, with a 250 ms pause between them, and writes zero at the end. Mechanical gearing varies among 28BYJ-48 versions, so the exact number of steps per revolution must be measured on the unit in use.

## 5. Verification

The simulation checks the sequence produced by the self-test on all four top-level pins. The physical test confirms movement, direction and coil wiring. The self-test lasts only a few microseconds and causes no relevant mechanical displacement before the timed movement.

```bash
cd ~/PFE/Stepper-Motor/Tests
export PATH="$HOME/.local/opt/insper-riscv32-elf/bin:$HOME/.local/opt/insper-spike/bin:$PATH"
riscv-tools --config tools/riscv_build/config.stepper-motor.yaml generate-header
riscv-tools --config tools/riscv_build/config.stepper-motor.yaml compile --emit mif
riscv-tools --config tools/riscv_build/config.stepper-motor.yaml program build-stepper/real/stepper-motor.mif
```

After programming, the motor turns approximately one quarter revolution, pauses, returns and stays de-energized. If it only vibrates, check the IN1 through IN4 order. If the observed direction is reversed, the wiring is functional and the direction names can be swapped in software.

---

Copyright 2026 Insper. Licensed under the [Apache License, Version 2.0](../../../LICENSE).
