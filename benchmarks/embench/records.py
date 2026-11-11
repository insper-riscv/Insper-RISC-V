"""Protect cached result records from accidental corruption."""

import hashlib
import json
from typing import Any


def checksum(document: dict[str, Any]) -> str:
    """Hash all result fields except the checksum itself."""
    content = {k: v for k, v in document.items() if k != "record_sha256"}
    data = json.dumps(content, sort_keys=True, allow_nan=False).encode()
    return hashlib.sha256(data).hexdigest()


def intact(document: dict[str, Any]) -> bool:
    """Reject corrupt, unsealed or nonfinite records."""
    try:
        return document.get("record_sha256") == checksum(document)
    except ValueError, TypeError:
        return False
