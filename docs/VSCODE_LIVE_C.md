# VS Code Live C environment

The maintained workflow is documented in [SDK.md](../SDK.md). The extension source and installation instructions are in [insper-riscv/Live](https://github.com/insper-riscv/Live).

Use `scripts/rv32-new c /path/to/app` for a new application, or open the preserved [Live example](../examples/live-c/README.md). Install the matching VSIX from `share/rv32-development.vsix` in the host/SSH window and its Dev Container. The editor toolbar provides Program FPGA, Fast Update and Simulate.

This supersedes the original PR frontend, whose commands referenced the removed Tests and TopLevel submodules. The processor's current `src/` platforms and module pointers are preserved. Application changes and generated hardware stay in private SDK/project directories. CPU selection is `project.cpu_profile`; the memory/peripheral map is selected separately by `project.platform`. No processor-main files are replaced by the legacy platform layout.
