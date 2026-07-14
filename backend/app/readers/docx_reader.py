from __future__ import annotations

from pathlib import Path

from docx import Document

from app.readers.base import DatasetRows


class DocxReader:
    extension = ".docx"

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
        doc = Document(str(path))
        return [
            (paragraph.text or "").strip()
            for paragraph in doc.paragraphs
            if (paragraph.text or "").strip()
        ]
