# FPGA setup is not required for Embench CI

The current `embench` PR workflow uses hosted GHDL simulation only.
It does not call a physical workflow or require an organization runner.
Do not provision FPGA access just to enable this check.

The manual hardware harness and [physical validation](DUAL-VALIDATION.md)
remain available as historical evidence. The former setup instructions are
preserved in Git history at commit
`c6c87452c4355570db3a8a7ecd08432b7c2a089f`.

See [AUTOMATION.md](AUTOMATION.md) for the current CI contract.
