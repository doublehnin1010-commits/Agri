from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class DatasetRows:
    proverbs: list[str]
    meanings: list[str]
    english_meanings: list[str]


class DocumentReader(Protocol):
    extension: str

    def read_dataset(
        self,
        proverbs_path: Path,
        meanings_path: Path,
        english_meanings_path: Path,
    ) -> DatasetRows:
        """Read the three required dataset files into aligned text lists."""
