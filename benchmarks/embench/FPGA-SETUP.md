# Administrator action: allow the reviewed FPGA workflow

Repository: `insper-riscv/Insper-RISC-V` (public).
Existing runner: `D-20003267-LINUX`, organization group `FPGA`.
Required custom runner label: `rv32-de0-cv`.

The account performing the integration receives HTTP 403 from the runner
group administration API. The repository currently lists zero accessible
self-hosted runners. This requires an organization administrator; SSH
access to the workstation alone does not grant GitHub runner access.

In organization Settings → Actions → Runner groups → FPGA:

1. Add this repository to the selected repositories and enable use by this
   public repository. Preserve all other repositories already allowed.
   Add the custom label `rv32-de0-cv` to `D-20003267-LINUX` only. The workflow
   also verifies the runner name before doing any lab work.
2. Restrict workflow access to selected reviewed workflows. Preserve the
   existing approved workflows and append this exact immutable reference:

   ```text
   insper-riscv/Insper-RISC-V/.github/workflows/embench-hardware.yml@ddab4dbcf30674c44351367ede0f4fb20244504c
   ```

3. Do not allow the caller `embench.yml`, arbitrary PR workflow files or a
   mutable branch reference onto the persistent self-hosted runner.
4. After access is confirmed, set the repository Actions variable
   `EMBENCH_FPGA_ENABLED=true`. Until then the hosted authorization job fails
   immediately, rather than leaving physical jobs queued for hours.

The allowlisted workflow pins its host/measurement driver to:
`d725e986893bd69daaf7144f951b7d6f7fb31f8a`.

Source for review:
[trusted workflow](https://github.com/insper-riscv/Insper-RISC-V/blob/ddab4dbcf30674c44351367ede0f4fb20244504c/.github/workflows/embench-hardware.yml),
[measurement driver](https://github.com/insper-riscv/Insper-RISC-V/tree/d725e986893bd69daaf7144f951b7d6f7fb31f8a/benchmarks/embench).

The shared runner must remain running and registered in its current group.
No personal access token, SSH private key or broad administrator credential
needs to be copied to the workstation. Docker and Quartus are already
installed. Fork PRs are rejected before any lab job starts.

After the runner is visible to the repository, manually dispatch `embench`
on `embench-ci`, with `scope=named`, `workload=ci`, `compare_ref=main`.
This tests both PR sides without opening a PR or merging anything. Wait for
the combined `embench` check, including all physical jobs, to pass before
calling the GitHub integration validated.

See [AUTOMATION.md](AUTOMATION.md) for the board locks, identity checks,
resource limits, metric definitions and isolated compilation design.
