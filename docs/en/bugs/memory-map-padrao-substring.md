# The memory map check read the SDRAM as if it were the RAM

## 1. Summary

The memory map check compares the RAM base written in the core VHDL against the platform map, looking for the constant by a text pattern. When the core gained the SDRAM base constant, the RAM pattern started matching it too.

| | |
| :--- | :--- |
| Symptom | `check-memory-map` reports "expected the RAM base (0x8000), found 0x40000000" |
| Cause | The name of the RAM constant is contained in the name of the SDRAM constant, and the pattern does not mark the start of the word |
| Fix | The pattern now starts at a word boundary |
| Impact avoided | The `internal-mem` platform check would break by itself as soon as the core with the SDRAM was integrated |

## 2. The mechanism

The core declares a constant for the internal RAM base and, now, another for the SDRAM base. The name of the second ends exactly with the name of the first:

| Constant | Value | Name |
| :--- | :--- | :--- |
| internal RAM base | `0x8000` | ends in `RAM_BASE_BYTES` |
| SDRAM base | `0x40000000` | ends in `RAM_BASE_BYTES`, with `SD` in front |

The pattern that looked for the first did not require the name to start there. The search took the first occurrence of the text in the file. Since the SDRAM one appears first, the value read was `0x40000000`.

## 3. When it happens

Only after the core declares both constants. Before that, the pattern matched exactly once and the check passed.

## 4. The fix

The pattern of both maps (the `internal-mem` one and the `sdram` one) now requires a word boundary before the name. There is no boundary between `D` and `R` inside `SDRAM`, so only the RAM constant matches.

## 5. How the proof shows up

| Situation | Result |
| :--- | :--- |
| old pattern, core with both constants | 1 divergence |
| new pattern, same core | `internal-mem`: 43 checks ok, `sdram`: 47 ok |

## 6. How to avoid it

A pattern that looks for a name in source code must mark the start and the end of the word. Any new name that contains an old name (or is contained by it) can divert a text search.

---

Copyright 2026 Insper. Licensed under the [Apache License, Version 2.0](../../../LICENSE).
