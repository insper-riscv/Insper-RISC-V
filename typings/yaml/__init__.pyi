"""Tipos do trecho do PyYAML que os scripts usam."""

from typing import Any

def safe_load(stream: str) -> Any:
    """Lê um documento YAML sem construir objetos arbitrários."""
