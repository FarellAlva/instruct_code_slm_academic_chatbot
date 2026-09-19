"""
rag/loader.py — Load PDF files and web-scraped text files.

Supports:
  - PDFs from /data/ (via pypdf)
  - Text files from /data/web/ (scraped from pradita.ac.id)

Only the developer runs this; end-users never upload files.
"""

import os
import re
from typing import List, Dict, Any
from pathlib import Path

# pypdf is lightweight and pure-python—no system poppler required.
try:
    from pypdf import PdfReader
except ImportError:
    # pyrefly: ignore [missing-import]
    from PyPDF2 import PdfReader  # fallback for older installs


def load_pdfs(data_dir: str) -> List[Dict[str, Any]]:
    """
    Scan *data_dir* for PDF files and extract their text.

    Returns a list of dicts:
      {
        "text":   str,          # full extracted text of the page
        "source": str,          # original filename
        "page":   int           # 1-based page number
      }
    """
    data_path = Path(data_dir)
    if not data_path.exists():
        raise FileNotFoundError(f"Data directory not found: {data_dir}")

    pdf_files = list(data_path.rglob("*.pdf"))
    if not pdf_files:
        print(f"[Loader] ⚠  No PDF files found recursively in {data_dir}")
        return []

    documents: List[Dict[str, Any]] = []
    for pdf_path in pdf_files:
        print(f"[Loader] 📄 Reading: {pdf_path.name}")
        try:
            reader = PdfReader(str(pdf_path))
            for page_num, page in enumerate(reader.pages, start=1):
                text = page.extract_text() or ""
                text = text.strip()
                if text:
                    documents.append(
                        {
                            "text":   text,
                            "source": pdf_path.name,
                            "page":   page_num,
                        }
                    )
        except Exception as exc:
            print(f"[Loader] ❌ Failed to read {pdf_path.name}: {exc}")

    print(f"[Loader] ✅ Loaded {len(documents)} pages from {len(pdf_files)} PDF(s).")
    return documents


def load_web_texts(web_dir: str) -> List[Dict[str, Any]]:
    """
    Load scraped text files from /data/web/.

    Each .txt file is treated as a single "page" document.

    Returns same format as load_pdfs():
      {
        "text":   str,
        "source": str,   # e.g. "web:facilities.txt"
        "page":   1
      }
    """
    web_path = Path(web_dir)
    if not web_path.exists():
        print(f"[Loader] ⚠  Web data directory not found: {web_dir}")
        return []

    txt_files = list(web_path.glob("*.txt"))
    if not txt_files:
        print(f"[Loader] ⚠  No text files found in {web_dir}")
        return []

    documents: List[Dict[str, Any]] = []
    for txt_path in txt_files:
        print(f"[Loader] 🌐 Reading: {txt_path.name}")
        try:
            text = txt_path.read_text(encoding="utf-8").strip()
            if text:
                documents.append(
                    {
                        "text":   text,
                        "source": f"web:{txt_path.name}",
                        "page":   1,
                    }
                )
        except Exception as exc:
            print(f"[Loader] ❌ Failed to read {txt_path.name}: {exc}")

    print(f"[Loader] ✅ Loaded {len(documents)} web text files.")
    return documents


def load_ocr_texts(ocr_dir: str) -> List[Dict[str, Any]]:
    """
    Load OCR-extracted text files from /data/jadwal_ocr/.

    These are PyMuPDF-extracted texts with better layout preservation
    than pypdf for table-structured jadwal PDFs.

    Returns same format as load_pdfs():
      {
        "text":   str,
        "source": str,   # original jadwal PDF name
        "page":   1
      }
    """
    ocr_path = Path(ocr_dir)
    if not ocr_path.exists():
        print(f"[Loader] ⚠  OCR directory not found: {ocr_dir}")
        return []

    txt_files = sorted(ocr_path.glob("*.txt"))
    if not txt_files:
        print(f"[Loader] ⚠  No OCR text files found in {ocr_dir}")
        return []

    documents: List[Dict[str, Any]] = []
    for txt_path in txt_files:
        print(f"[Loader] 🔍 Reading OCR: {txt_path.name}")
        try:
            raw_content = txt_path.read_text(encoding="utf-8").strip()
            if not raw_content:
                continue

            source_name = txt_path.stem + ".pdf"

            # Parse page markers: "--- Page N ---"
            page_splits = re.split(r"(?m)^---\s*Page\s+(\d+)\s*---", raw_content)

            if len(page_splits) > 1:
                # page_splits format: [preamble, page_num_1, page_text_1, page_num_2, page_text_2, ...]
                preamble = page_splits[0].strip()
                if preamble:
                    documents.append(
                        {
                            "text":   preamble,
                            "source": source_name,
                            "page":   1,
                        }
                    )

                for i in range(1, len(page_splits), 2):
                    page_num = int(page_splits[i])
                    page_text = page_splits[i + 1].strip() if i + 1 < len(page_splits) else ""
                    if page_text:
                        documents.append(
                            {
                                "text":   page_text,
                                "source": source_name,
                                "page":   page_num,
                            }
                        )
            else:
                documents.append(
                    {
                        "text":   raw_content,
                        "source": source_name,
                        "page":   1,
                    }
                )
        except Exception as exc:
            print(f"[Loader] ❌ Failed to read {txt_path.name}: {exc}")

    print(f"[Loader] ✅ Loaded {len(documents)} OCR text files.")
    return documents


def load_all(data_dir: str) -> List[Dict[str, Any]]:
    """
    Load ALL knowledge sources — PDFs + web-scraped text + OCR.

    Priority for jadwal files:
      1. OCR text (data/jadwal_ocr/) — preferred, better table extraction
      2. Direct PDF extraction (data/jadwal/) — fallback

    This is the main entry point for the ingestion pipeline.
    """
    documents = []

    # 1. Check for OCR-extracted jadwal texts first
    ocr_dir = os.path.join(data_dir, "jadwal_ocr")
    ocr_docs = load_ocr_texts(ocr_dir)

    if ocr_docs:
        # Use OCR texts instead of jadwal PDFs
        ocr_sources = {doc["source"] for doc in ocr_docs}
        print(f"[Loader] 📋 Using OCR text for {len(ocr_sources)} jadwal files (skipping PDF extraction for these)")
        documents.extend(ocr_docs)

        # Load non-jadwal PDFs normally
        non_jadwal_docs = [
            doc for doc in load_pdfs(data_dir)
            if doc["source"] not in ocr_sources
        ]
        documents.extend(non_jadwal_docs)
    else:
        # No OCR available, load all PDFs normally
        documents.extend(load_pdfs(data_dir))

    # 2. Web text files from /data/web/
    web_dir = os.path.join(data_dir, "web")
    documents.extend(load_web_texts(web_dir))

    print(f"[Loader] 📊 Total documents loaded: {len(documents)}")
    return documents
