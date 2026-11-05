# Guides

The guides explain how to do a task from start to end with this repository.

| Guide | What it is for |
| :--- | :--- |
| [placa.md](placa.md) | Compile the Quartus project, program the DE0-CV and run programs on it, with the rule of compiling and programming in the same shell |
| [simulacao.md](simulacao.md) | Simulate the hardware top with the real Quartus memories in GHDL |
| [kpis.md](kpis.md) | Generate and compare the KPI reports (clock, test coverage and supported instructions) |
| [nova-arquitetura.md](nova-arquitetura.md) | Create a new platform from the model `src/simulation/template/`, from the memory map to certification and the board |

The platforms themselves, with memory map, boot and runtime, are in [../platform/](../platform/README.md). The defects already diagnosed are in [../bugs/](../bugs).
