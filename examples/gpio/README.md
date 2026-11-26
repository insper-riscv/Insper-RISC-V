# RV32 gpio example

Open this directory directly in VS Code and use **Dev Containers: Reopen in
Container**. The SDK must be registered on the Docker host with
`scripts/install-user.sh`. Then run **RV32: Prepare Project** and **RV32: Simulate**.

This project uses the modular simulation platform; FPGA actions are rejected.
Select `cpu_profile` in `rv32.toml`. CLINT/PLIC require `rv32im_zicsr_irq`.
Generated per-driver projects appear under `vendor/<DRIVER>/example/` after
preparation. Open or copy one of those folders as its own project.
