"""Read plain-text and gzip-compressed log files."""

from __future__ import annotations

import gzip
from pathlib import Path
from typing import Iterator, Union


def iter_rows(path: Union[str, Path]) -> Iterator[str]:
    """Yield non-empty lines from one file or every log file in a directory."""
    source = Path(path)
    files = sorted(source.glob("*")) if source.is_dir() else [source]
    for file_path in files:
        if not file_path.is_file() or file_path.name.startswith("."):
            continue
        opener = gzip.open if file_path.suffix == ".gz" else open
        with opener(file_path, mode="rt", encoding="utf-8", errors="replace") as stream:
            yield from (line.rstrip("\n") for line in stream if line.strip())


def to_rows(path: Union[str, Path]) -> list[str]:
    """Return all available log lines, preserving file order."""
    return list(iter_rows(path))


toRows = to_rows
