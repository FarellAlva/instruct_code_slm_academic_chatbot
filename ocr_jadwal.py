"""
ocr_jadwal.py — Extract clean text from jadwal (schedule) PDFs using PyMuPDF.

PyMuPDF's layout-preserving text extraction is far superior to pypdf for
table-structured PDFs. This script extracts text from all jadwal PDFs in
data/jadwal/ and saves cleaned text files to data/jadwal_ocr/.

Usage:
    python ocr_jadwal.py                    # process all jadwal PDFs
    python ocr_jadwal.py --file "1. TI"     # process specific file (partial match)
    python ocr_jadwal.py --compare          # compare pypdf vs pymupdf extraction

Output:
    data/jadwal_ocr/<filename>.txt  — one text file per PDF
"""

import os
import sys
import argparse
import re
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pymupdf  # PyMuPDF

JADWAL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "jadwal")
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "jadwal_ocr")


def extract_text_pymupdf(pdf_path: str) -> list[dict]:
    """
    Extract text from PDF using PyMuPDF with layout preservation.

    Uses 'text' extraction with sort=True for proper reading order,
    which handles table layouts much better than pypdf.

    Returns list of {page: int, text: str}
    """
    doc = pymupdf.open(pdf_path)
    pages = []

    for page_num in range(len(doc)):
        page = doc[page_num]

        # Method 1: Standard text extraction with sorting (good for most PDFs)
        text = page.get_text("text", sort=True)

        # Method 2: If text is too sparse, try blocks-based extraction
        if not text.strip() or len(text.strip()) < 50:
            # Try extracting as blocks and reconstructing
            blocks = page.get_text("blocks", sort=True)
            lines = []
            for block in blocks:
                if block[6] == 0:  # text block (not image)
                    lines.append(block[4].strip())
            text = "\n".join(lines)

        if text.strip():
            pages.append({
                "page": page_num + 1,
                "text": text.strip(),
            })

    doc.close()
    return pages


def extract_text_pypdf(pdf_path: str) -> list[dict]:
    """Extract text using pypdf for comparison."""
    try:
        from pypdf import PdfReader
    except ImportError:
        # pyrefly: ignore [missing-import]
        from PyPDF2 import PdfReader

    reader = PdfReader(pdf_path)
    pages = []
    for page_num, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if text.strip():
            pages.append({
                "page": page_num,
                "text": text.strip(),
            })
    return pages


def clean_extracted_text(text: str) -> str:
    """
    Clean extracted text for better downstream parsing.

    - Remove excessive whitespace while preserving table structure
    - Normalize unicode characters
    - Remove page headers/footers if repeated
    """
    # Normalize various dash/hyphen characters
    text = text.replace('\u2013', '-').replace('\u2014', '-')
    # Normalize whitespace but keep newlines
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        # Collapse multiple spaces to single (but preserve some structure)
        line = re.sub(r' {3,}', '  ', line)
        # Remove leading/trailing whitespace per line
        line = line.strip()
        if line:
            cleaned_lines.append(line)

    return '\n'.join(cleaned_lines)


def process_jadwal_pdfs(
    jadwal_dir: str = JADWAL_DIR,
    output_dir: str = OUTPUT_DIR,
    file_filter: str = None,
) -> list[str]:
    """
    Process all jadwal PDFs and save extracted text.

    Args:
        jadwal_dir: Directory containing jadwal PDF files
        output_dir: Directory to save extracted text files
        file_filter: Optional partial filename match

    Returns:
        List of output file paths
    """
    os.makedirs(output_dir, exist_ok=True)

    pdf_files = sorted(Path(jadwal_dir).glob("*.pdf"))
    if file_filter:
        pdf_files = [f for f in pdf_files if file_filter.lower() in f.name.lower()]

    if not pdf_files:
        print(f"[OCR] ⚠ No PDF files found in {jadwal_dir}")
        if file_filter:
            print(f"[OCR]   Filter: '{file_filter}'")
        return []

    print(f"[OCR] Found {len(pdf_files)} jadwal PDFs to process")
    print(f"[OCR] Output directory: {output_dir}")
    print("=" * 60)

    output_files = []

    for pdf_path in pdf_files:
        print(f"\n[OCR] 📄 Processing: {pdf_path.name}")

        try:
            pages = extract_text_pymupdf(str(pdf_path))

            if not pages:
                print(f"[OCR]   ⚠ No text extracted from {pdf_path.name}")
                continue

            # Combine all pages
            full_text = ""
            for page_data in pages:
                cleaned = clean_extracted_text(page_data["text"])
                full_text += f"\n--- Page {page_data['page']} ---\n{cleaned}\n"

            # Save output
            output_name = pdf_path.stem + ".txt"
            output_path = os.path.join(output_dir, output_name)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(full_text.strip())

            output_files.append(output_path)

            # Stats
            line_count = len(full_text.strip().split('\n'))
            char_count = len(full_text.strip())
            print(f"[OCR]   ✅ Saved: {output_name} ({line_count} lines, {char_count} chars)")

            # Quick quality check: look for schedule row patterns
            row_pattern = re.compile(
                r"\d+\s+(?:Senin|Selasa|Rabu|Kamis|Jumat|Sabtu)\s+\d{2}\.\d{2}"
            )
            row_matches = row_pattern.findall(full_text)
            print(f"[OCR]   📊 Schedule rows detected: {len(row_matches)}")

        except Exception as e:
            print(f"[OCR]   ❌ Error processing {pdf_path.name}: {e}")

    print(f"\n{'=' * 60}")
    print(f"[OCR] ✅ Processed {len(output_files)}/{len(pdf_files)} files")
    print(f"[OCR] Output: {output_dir}")

    return output_files


def compare_extraction(pdf_path: str):
    """Compare pypdf vs pymupdf extraction for a single file."""
    print(f"\n{'=' * 60}")
    print(f"Comparing extraction: {os.path.basename(pdf_path)}")
    print(f"{'=' * 60}")

    # pypdf
    print("\n--- pypdf extraction (first 1000 chars) ---")
    pypdf_pages = extract_text_pypdf(pdf_path)
    pypdf_text = "\n".join(p["text"] for p in pypdf_pages)
    print(pypdf_text[:1000])

    # pymupdf
    print("\n--- PyMuPDF extraction (first 1000 chars) ---")
    pymupdf_pages = extract_text_pymupdf(pdf_path)
    pymupdf_text = "\n".join(p["text"] for p in pymupdf_pages)
    pymupdf_clean = clean_extracted_text(pymupdf_text)
    print(pymupdf_clean[:1000])

    # Stats comparison
    row_pattern = re.compile(
        r"\d+\s+(?:Senin|Selasa|Rabu|Kamis|Jumat|Sabtu)\s+\d{2}\.\d{2}"
    )
    pypdf_rows = len(row_pattern.findall(pypdf_text))
    pymupdf_rows = len(row_pattern.findall(pymupdf_clean))

    print(f"\n--- Comparison ---")
    print(f"pypdf:   {len(pypdf_text)} chars, {pypdf_rows} schedule rows detected")
    print(f"PyMuPDF: {len(pymupdf_clean)} chars, {pymupdf_rows} schedule rows detected")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OCR/Extract text from jadwal PDFs")
    parser.add_argument("--file", type=str, help="Process specific file (partial name match)")
    parser.add_argument("--compare", action="store_true",
                        help="Compare pypdf vs pymupdf extraction on first file")
    args = parser.parse_args()

    if args.compare:
        pdf_files = sorted(Path(JADWAL_DIR).glob("*.pdf"))
        if args.file:
            pdf_files = [f for f in pdf_files if args.file.lower() in f.name.lower()]
        if pdf_files:
            compare_extraction(str(pdf_files[0]))
        else:
            print("No PDF files found for comparison")
    else:
        process_jadwal_pdfs(file_filter=args.file)
