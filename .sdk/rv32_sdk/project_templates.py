"""Keep exported applications and their driver examples on the same local SDK."""

import json
import re
from pathlib import PurePosixPath
from typing import Any


def options(project: dict[str, Any], *, child: bool = False) -> dict[str, Any]:
    """Propagate the actual hardware map into independently opened examples."""
    result = {}
    if project.get("platform") == "project":
        result["platform_file"] = project["platform_file"]
    relative = project.get("sdk_relative_root")
    if relative is not None:
        if (
            not isinstance(relative, str)
            or not re.fullmatch(r"[A-Za-z0-9_. /-]+", relative)
            or PurePosixPath(relative).is_absolute()
        ):
            raise SystemExit("Invalid project.sdk_relative_root")
        result["sdk_relative_root"] = (
            "../../../" + relative if child else relative
        )
    return result


def configure(files: dict[str, bytes], project: dict[str, Any]) -> None:
    """Use a relative SDK bind mount, so moving the complete project is safe."""
    relative = options(project).get("sdk_relative_root")
    if relative is None:
        return
    name = ".devcontainer/compose.yaml"
    old = '"${HOME}/.local/share/rv32-sdk:/opt/rv32-sdk:cached"'
    new = json.dumps("../" + relative + ":/opt/rv32-sdk:cached")
    text = files[name].decode()
    if old not in text:
        raise SystemExit(
            "SDK Compose template changed; cannot set its local SDK mount"
        )
    files[name] = text.replace(old, new, 1).encode()
