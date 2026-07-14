from __future__ import annotations

from pathlib import Path

from app.readers.base import DatasetRows


class TxtReader:
    extension = ".txt"

    def read_dataset(
        self,
        proverbs_path: Path,
        meanings_path: Path,
        english_meanings_path: Path,
    ) -> DatasetRows:
        return DatasetRows(
            proverbs=self._read_lines(proverbs_path),
            meanings=self._read_lines(meanings_path),
            english_meanings=self._read_lines(english_meanings_path),
        )

    def _read_lines(self, path: Path) -> list[str]:
        text = path.read_text(encoding="utf-8-sig")
        return [line.strip() for line in text.splitlines() if line.strip()]
