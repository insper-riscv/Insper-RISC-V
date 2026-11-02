# The SDRAM read on the board arrived one cycle earlier than the simulation assumed

## 1. Summary

The controller passed every simulation and, on its first run on the board, returned wrong words. The two halves of each word came back equal to the second half.

| | |
| :--- | :--- |
| Symptom | In the fast mode of the self-test, 196,352 of the 196,608 words read came back wrong. At address 0, `0x00A5C35A` was expected and `0x00A500A5` was read |
| Cause | With the phase chosen for the chip clock, the read data arrives one cycle earlier than the simulation model assumes |
| Fix | Sample the read data one cycle earlier on the board (without the extra cycle the model uses when the pin goes through a register) |
| Result | The four self-test modes pass, including the sweep of 67,108,864 words |

## 2. The mechanism

A word read is a burst of two 16-bit halves. The controller samples them in two consecutive cycles, a fixed number of cycles after the command.

| Environment | What the model assumes | What happens |
| :--- | :--- | :--- |
| simulation | The chip sees the command on the edge after the one the controller issued it on, and returns the data three cycles later | The read data sits on the pins exactly where the controller samples it |
| board, phase of 2750 ps | The clock reaching the chip is shifted relative to the controller one, and the chip sees the command on the edge with the same number it was issued on | The data arrives one cycle earlier |

With the data one cycle earlier, the sample of the first cycle caught the second half of the burst, and the sample of the second cycle caught a value the bus was still holding (the same second half). The two halves of the word came out equal, which is what the test showed.

## 3. Why the simulation did not see it

The chip model and the controller share the same timing convention, and the shift of the clock that goes to the chip does not exist in simulation, where the clock is the same. The only thing that tells the two cases apart is the real clock phase on the board.

## 4. The fix

In the board top the controller samples the data without the extra capture cycle. The register that Quartus places in the I/O cell of the data pin is still there. Only the number of wait cycles before reading the result decreases. The right value depends on the chip clock phase, which is the only parameter adjusted on the board.

## 5. How the proof shows up

| Capture | Wrong words, fast mode |
| :--- | ---: |
| with the extra cycle | 196,352 of 196,608 |
| without the extra cycle | 0 |

## 6. How to avoid it

A latency value that depends on a clock phase is not validated in simulation alone. On the first run on the board of an external memory controller, the self-test must be the first step, and the capture must be a parameter with the measured value, not an assumption.

---

Copyright 2026 Insper. Licensed under the [Apache License, Version 2.0](../../../LICENSE).
