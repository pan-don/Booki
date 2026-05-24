from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict

import fitz  # PyMuPDF

from utils.logger import get_logger

logger = get_logger(__name__)


class PDFParser:
    """Ekstrak teks dari PDF menggunakan PyMuPDF, output format ramping."""

    def __init__(self, pdf_path: str | Path):
        self.pdf_path = Path(pdf_path)
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"File tidak ditemukan: {self.pdf_path}")

    def parse(self) -> Dict[str, Any]:
        logger.debug(f"Parsing {self.pdf_path.name} with PyMuPDF")
        with fitz.open(self.pdf_path) as doc:
            pages = []
            for page_num, page in enumerate(doc, start=1):
                text = page.get_text("text").strip()
                pages.append({"page_num": page_num, "text": text})
        logger.debug(f"Extracted {len(pages)} pages from {self.pdf_path.name}")
        return {
            "source": str(self.pdf_path.resolve()),
            "file_name": self.pdf_path.name,
            "num_pages": len(pages),
            "pages": pages
        }

    def save_json(self, output_path: str | Path) -> None:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        data = self.parse()
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.debug(f"Saved parsed JSON to {output_path}")


def parse_pdf_to_json(pdf_path: str | Path, json_output: str | Path) -> None:
    parser = PDFParser(pdf_path)
    parser.save_json(json_output)

def parse_pdf_to_text(pdf_path: str | Path) -> str:
    """Extrak seluruh teks dari PDF menjadi satu string secara berurutan."""
    parser = PDFParser(pdf_path)
    data = parser.parse()
    text_content = "\n\n".join([page.get("text", "") for page in data.get("pages", [])])
    return text_content


if __name__ == "__main__":
    # parse_pdf_to_json("contoh.pdf", "output.json")
    pass