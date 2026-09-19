"""
tests/test_basic.py — Smoke tests to verify environment and baseline behavior.
"""

import os
import pytest
from rag.chunker import _is_schedule_file, _clean_inline_text, _extract_prodi_name, PRODI_MAP


def test_schedule_file_detection():
    assert _is_schedule_file("1. TI - Jadwal Perkuliahan Genap 2025-2.rev.pdf") is True
    assert _is_schedule_file("about_pradita.txt") is False
    assert _is_schedule_file("calendar_academic.pdf") is True


def test_clean_inline_text():
    raw = "  Interaksi   Manusia    dan Komputer.  "
    assert _clean_inline_text(raw) == "Interaksi Manusia dan Komputer"


def test_extract_prodi_name():
    source = "1. TI - Jadwal Perkuliahan Genap 2025-2.rev.pdf"
    text = "Program Studi Informatika\nUNIVERSITAS PRADITA"
    prodi = _extract_prodi_name(source, text)
    assert "Informatika" in prodi


def test_mock_llm(mock_ollama_chat):
    from llm.ollama_client import chat_with_context
    ans = chat_with_context(user_query="Halo")
    assert "simulasi" in ans
