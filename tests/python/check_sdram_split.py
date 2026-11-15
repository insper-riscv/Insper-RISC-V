"""Confere que a divisão FLASH e RAM da SDRAM vem do platform.yaml.

Uso, da raiz do repositório, na imagem `dev_tools`:

    python tests/python/check_sdram_split.py

O padrão da DE0-CV é 32 MiB de FLASH e 32 MiB de RAM no chip de 64 MiB.
Este script reescreve só os tamanhos do `platform.yaml` em outras
divisões e confere que o `riscv-tools` aceita as que cabem no chip,
recusa as que não cabem e escreve o `config_pkg` com os limites novos.
"""

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
PLATFORM = ROOT / "src/cyclone-v/de0-cv/platform.yaml"
MIB = 1 << 20
CHIP = 64 * MIB
FLASH_BASE = 0x1000
RAM_BASE = 0x40000000
# Tamanho do cabeçalho de uma banca, e os fins das palavras reservadas
# abaixo do fim da RAM.
STDOUT_BELOW, TOHOST_BELOW, FROMHOST_BELOW = 0x420, 0x18, 0x10
# Divisões a testar: (fim da FLASH, tamanho da RAM, cabe no chip).
SPLITS = [
    (32 * MIB, 32 * MIB, True),
    (16 * MIB, 48 * MIB, True),
    (48 * MIB, 16 * MIB, True),
    (4 * MIB, 4 * MIB, True),
    (40 * MIB, 40 * MIB, False),
    (64 * MIB, 32 * MIB, False),
]


def variant(flash_end: int, ram_size: int) -> dict[str, Any]:
    """Build the platform with another split of the chip.

    Parameters
    ----------
    flash_end : int
        End of the FLASH, in bytes (it starts at 0x1000).
    ram_size : int
        Size of the RAM, in bytes.

    Returns
    -------
    dict of {str: Any}
        The platform of the DE0-CV with the new sizes and no `checks`.
    """
    data = yaml.safe_load(PLATFORM.read_text(encoding="utf-8"))
    memory = data["memory"]
    memory["instructions"][0]["size"] = flash_end - FLASH_BASE
    memory["data"][0]["size"] = ram_size
    # A FLASH e a RAM dividem o chip, então cada uma diz onde começa nele:
    # a FLASH no próprio endereço do SoC e a RAM logo depois dela.
    memory["instructions"][0]["offset"] = FLASH_BASE
    memory["data"][0]["offset"] = flash_end
    ram_end = RAM_BASE + ram_size
    data["reserved"] = {
        "stdout": {"base": ram_end - STDOUT_BELOW, "size": "1K+8"},
        "tohost": {"base": ram_end - TOHOST_BELOW, "size": 8},
        "fromhost": {"base": ram_end - FROMHOST_BELOW, "size": 8},
    }
    middle = (flash_end + FLASH_BASE) // 2 // 4096 * 4096
    data["flash"]["banks"] = [
        {"name": "A", "base": FLASH_BASE, "size": middle - FLASH_BASE},
        {"name": "B", "base": middle, "size": flash_end - middle},
    ]
    data["checks"] = []
    data["profiles"] = str(ROOT / "Core/profiles/matrix.yaml")
    data.pop("generate", None)
    data.pop("config", None)
    return data


def run(*args: str) -> subprocess.CompletedProcess[str]:
    """Run `riscv-tools` from the root of the repository.

    Parameters
    ----------
    *args : str
        The arguments after `--root .`.

    Returns
    -------
    subprocess.CompletedProcess of str
        The finished process, with the output captured.
    """
    tool = shutil.which("riscv-tools") or "riscv-tools"
    return subprocess.run(  # noqa: S603
        [tool, "--root", str(ROOT), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def check_split(
    directory: Path, flash_end: int, ram_size: int, fits: bool
) -> bool:
    """Check one split of the chip.

    Parameters
    ----------
    directory : Path
        Where the variant of the platform is written.
    flash_end : int
        End of the FLASH, in bytes.
    ram_size : int
        Size of the RAM, in bytes.
    fits : bool
        Whether the two regions fit in the chip.

    Returns
    -------
    bool
        True when the tool accepts a split that fits (and writes the
        new limits in the `config_pkg`) or refuses one that does not.
    """
    name = f"{flash_end // MIB}M-{ram_size // MIB}M"
    path = directory / f"{name}.yaml"
    path.write_text(json.dumps(variant(flash_end, ram_size)))
    package = directory / f"{name}_config_pkg.vhd"
    check = run("check-memory-map", "--platform", str(path))
    written = run(
        "generate-config-pkg",
        "--platform",
        str(path),
        "--output",
        str(package),
    )
    ok = (check.returncode == 0) == fits
    if fits:
        text = package.read_text() if package.exists() else ""
        ok = ok and f'x"{flash_end:08X}"' in text
        ok = ok and f'x"{RAM_BASE + ram_size:08X}"' in text
    status = "ok" if ok else "FAILED"
    print(f"{status}: FLASH end {flash_end:#x}, RAM {ram_size:#x}")
    if not ok:
        print(check.stdout + check.stderr + written.stderr)
    return ok


def main() -> int:
    """Check every split.

    Returns
    -------
    int
        0 when all of them behave as expected, 1 otherwise.
    """
    with tempfile.TemporaryDirectory() as directory:
        results = [
            check_split(Path(directory), flash_end, ram_size, fits)
            for flash_end, ram_size, fits in SPLITS
        ]
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
