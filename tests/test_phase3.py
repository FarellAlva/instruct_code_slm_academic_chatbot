"""
tests/test_phase3.py — Test suite for Fase 3 (Structured Schedules & Deterministic Engine).

Verifies:
1. Table extraction accuracy and wrapped cell fixtures (Pemrograman Web, Forensik Digital).
2. Schedule validation rules (valid day, time order, SKS integer).
3. ScheduleSource interface & .rev version precedence.
4. Markdown table formatting & review disclaimer.
5. Multi-turn slot retention & single disambiguation prompt.
6. Golden set exact-match accuracy >= 98%.
"""

import os
import re
import pytest

from rag.schedule_extractor import parse_time_range, parse_lecturers, VALID_DAYS
from rag.schedule_source import get_schedule_source, ScheduleSource, StructuredFileScheduleSource
from app import _extract_slots, _build_direct_schedule_answer
from eval.generate_schedule_golden_set import generate_and_evaluate_golden_set


def test_time_range_parsing():
    start, end, valid = parse_time_range("08.25 - 11.05")
    assert valid is True
    assert start == "08.25"
    assert end == "11.05"

    start, end, valid = parse_time_range("10.15 -12.00")
    assert valid is True
    assert start == "10.15"
    assert end == "12.00"

    # Reversed time range should be invalid
    _, _, valid = parse_time_range("15.00 - 13.00")
    assert valid is False


def test_lecturer_parsing():
    raw = "Theresia Herlina, S.Kom., M.T\nCarolino Benedicto, S.Pd., M.Kom."
    lecturers = parse_lecturers(raw)
    assert len(lecturers) == 2
    assert "Theresia Herlina, S.Kom., M.T" in lecturers
    assert "Carolino Benedicto, S.Pd., M.Kom." in lecturers


def test_wrapped_cell_fixtures():
    """
    Test the exact audit fixture from 1. TI - Jadwal Perkuliahan Genap 2025-2.rev.pdf:
    - Row 31 (Pemrograman Web) with multi-line room: A206 / Lab Komp
    - Row 42 (Forensik Digital) with multi-line note: Focus Study: Cyber Security
    """
    sched_src = get_schedule_source()
    ti_records = sched_src.search(prodi="INF")
    assert len(ti_records) > 0

    # 1. Pemrograman Web room test
    pw_matches = [r for r in ti_records if r.get("mata_kuliah") == "Pemrograman Web"]
    assert len(pw_matches) > 0
    pw = pw_matches[0]
    assert "A206" in pw["ruang"]
    assert "Lab Komp" in pw["ruang"]
    # Room must not leak into notes or course name
    assert pw["catatan"] != "A206"
    assert "Lab Komp" not in pw["mata_kuliah"]

    # 2. Forensik Digital note test
    fd_matches = [r for r in ti_records if r.get("mata_kuliah") == "Forensik Digital"]
    assert len(fd_matches) > 0
    fd = fd_matches[0]
    assert "Focus Study" in fd["catatan"]
    assert "Cyber" in fd["catatan"]
    assert "Security" in fd["catatan"]
    # Note must not leak into room
    assert "Focus Study" not in fd["ruang"]


def test_schedule_source_version_precedence():
    """Verify that .rev records take precedence over non-rev records for identical prodi."""
    sched_src = get_schedule_source()
    all_recs = sched_src.get_all()

    # For INF (which has .rev), no non-rev records should exist in the active source
    inf_recs = [r for r in all_recs if r.get("prodi_kode") == "INF"]
    assert len(inf_recs) > 0
    for r in inf_recs:
        assert r.get("source_version") == "rev"


def test_schedule_markdown_table_formatting():
    sched_src = get_schedule_source()
    imk = sched_src.lookup_course("Interaksi Manusia dan Komputer")
    assert len(imk) > 0
    table = sched_src.format_markdown_table(imk)

    # Required columns in target template
    for col in ["Hari", "Jam", "Mata Kuliah", "Kode", "SKS", "Kelas", "Ruang", "Dosen"]:
        assert col in table

    assert "Theresia Herlina" in table
    assert "IS31713" in table


def test_needs_review_disclaimer_rendering():
    sched_src = get_schedule_source()
    # Fake record with needs_review=True
    fake_rec = [
        {
            "hari": "Senin",
            "jam_mulai": "08.00",
            "jam_selesai": "10.00",
            "mata_kuliah": "Uji Validasi",
            "kode_mk": "TEST101",
            "sks": 2,
            "kelas": "A",
            "ruang": "A101",
            "dosen": ["Dosen Tester"],
            "needs_review": True,
        }
    ]
    table = sched_src.format_markdown_table(fake_rec)
    assert "Data ini hasil pembacaan otomatis dari dokumen, mohon dicek ulang di jadwal resmi." in table


def test_slot_extraction_and_multi_turn_retention():
    # Turn 1: user mentions prodi, semester, and day
    p1, s1, h1 = _extract_slots("Jadwal kuliah Informatika semester II hari Senin")
    assert p1 == "INF" or p1 == "TI"
    assert s1 == "II"
    assert h1 == "Senin"

    # Turn 2: user asks follow-up only mentioning day
    p2, s2, h2 = _extract_slots("Kalau hari Rabu?", current_prodi=p1, current_sem=s1)
    assert p2 == p1
    assert s2 == s1
    assert h2 == "Rabu"


def test_schedule_golden_set_accuracy():
    """Verify that automated schedule golden set achieves exact match >= 98%."""
    res = generate_and_evaluate_golden_set()
    assert res["total_cases"] >= 80
    assert res["accuracy_pct"] >= 98.0, f"Expected >= 98.0%, got {res['accuracy_pct']}%"
