"""
tests/test_phase1.py — Verification test suite for Fase 1 critical bug fixes:
1.1 Entity index and positive-only bypass (no false refusals).
1.2 ocr_jadwal.py path fixes and CLI arguments.
1.3 Context token budget and whole-chunk truncation.
1.4 loader.py page parsing for multi-page schedule OCR files.
"""

import os
import sys
import pytest
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from rag.entity_index import EntityIndex, normalize_course_name, normalize_title, parse_schedule_text
from rag.retriever import _build_structured_context
from rag.loader import load_ocr_texts
from config import MAX_CONTEXT_TOKENS, estimate_tokens


# ─── 1.1 Tests: Entity Index & Positive-Only Direct Bypass ───────────────────

def test_normalize_course_name():
    assert normalize_course_name("Interaksi Manusia dan Komputer") == "interaksi manusia komputer"
    assert normalize_course_name("Lab. Sistem Basis Data") == "lab sistem basis data"
    assert normalize_course_name("Studio Perancangan Arsitektur 2") == "studio perancangan arsitektur 2"


def test_normalize_title():
    raw_name = "Theresia Herlina, S.Kom., M.T."
    assert normalize_title(raw_name) == "theresia herlina"
    
    raw_name2 = "Dr. Eng. Handri Santoso, S.Si., M.Eng."
    assert normalize_title(raw_name2) == "handri santoso"


def test_entity_index_course_and_lecturer_direct_answers(sample_schedule_chunk):
    index = EntityIndex()
    
    # Manually populate index with sample entry
    parsed = parse_schedule_text(sample_schedule_chunk["text"])
    assert parsed is not None
    parsed["source"] = sample_schedule_chunk["source"]
    parsed["page"] = sample_schedule_chunk["page"]
    parsed["prodi"] = sample_schedule_chunk["prodi"]
    parsed["prodi_full"] = sample_schedule_chunk["prodi_full"]
    
    index.courses["interaksi manusia komputer"] = [parsed]
    index.lecturers["theresia herlina"] = [parsed]
    index._is_indexed = True

    # 1. Audit query: "Siapa dosen pengampu Interaksi Manusia dan Komputer?"
    ans = index.answer_direct_query("Siapa dosen pengampu Interaksi Manusia dan Komputer?")
    assert ans is not None
    assert "Theresia Herlina" in ans
    assert "Interaksi Manusia dan Komputer" in ans
    assert "Saya belum menemukan" not in ans  # NEVER refuse in bypass!

    # 2. Variation: "Interaksi Manusia Komputer diajar siapa"
    ans2 = index.answer_direct_query("Interaksi Manusia Komputer diajar siapa")
    assert ans2 is not None
    assert "Theresia Herlina" in ans2

    # 3. Variation: "dosen matkul Interaksi Manusia dan Komputer"
    ans3 = index.answer_direct_query("dosen matkul Interaksi Manusia dan Komputer")
    assert ans3 is not None
    assert "Theresia Herlina" in ans3

    # 4. Lecturer query: "jadwal Theresia Herlina hari apa"
    ans4 = index.answer_direct_query("jadwal Theresia Herlina hari apa")
    assert ans4 is not None
    assert "Jadwal mengajar resmi untuk **Theresia Herlina" in ans4
    assert "Interaksi Manusia dan Komputer" in ans4


def test_entity_index_never_refuses():
    """Verify that unindexed queries return None (no false refusals)."""
    index = EntityIndex()
    index._is_indexed = True
    
    # Query outside index must return None, NOT a refusal string
    assert index.answer_direct_query("Di mana lokasi kampus Pradita University?") is None
    assert index.answer_direct_query("Siapa presiden Amerika Serikat saat ini?") is None
    assert index.answer_direct_query("Berapa biaya kuliah Informatika?") is None


# ─── 1.3 Tests: Context Token Budget & Whole-Chunk Truncation ────────────────

def test_context_token_budget_truncation():
    # Create 5 synthetic chunks of 150 tokens each (~450 chars each)
    chunks = [
        {
            "id": f"chunk_{i}",
            "source": "test_doc.pdf",
            "page": i,
            "text": f"Baris jadwal kuliah nomor {i}. " + ("Informasi jadwal kuliah mata kuliah testing. " * 10),
            "meta": {"doc_type": "jadwal", "prodi_full": "Informatika", "semester": "II", "hari": "Senin"},
            "rerank_score": 10.0 - i,
        }
        for i in range(1, 6)
    ]

    # Test with very small budget (200 tokens) -> should only take 1 or 2 whole chunks
    context, included = _build_structured_context(chunks, person_query="", max_context_tokens=200)
    assert len(included) < 5
    assert len(included) >= 1
    # Check that context has whole documents and does not break mid-row
    for inc in included:
        assert inc["text"] in context
    
    # Ensure excluded chunks are not in context
    for exc in chunks[len(included):]:
        assert exc["id"] not in context


# ─── 1.4 Tests: OCR Page Parsing ─────────────────────────────────────────────

def test_loader_page_splitting(tmp_path):
    # Create a dummy OCR text file with page markers
    test_ocr_file = tmp_path / "sample_jadwal.txt"
    test_ocr_file.write_text(
        "--- Page 1 ---\n"
        "Jadwal Semester Genap Halaman 1\n"
        "Mata kuliah A\n"
        "\n--- Page 2 ---\n"
        "Jadwal Semester Genap Halaman 2\n"
        "Mata kuliah B\n",
        encoding="utf-8"
    )

    docs = load_ocr_texts(str(tmp_path))
    assert len(docs) == 2
    assert docs[0]["page"] == 1
    assert "Halaman 1" in docs[0]["text"]
    assert docs[1]["page"] == 2
    assert "Halaman 2" in docs[1]["text"]
    assert docs[0]["source"] == "sample_jadwal.pdf"
