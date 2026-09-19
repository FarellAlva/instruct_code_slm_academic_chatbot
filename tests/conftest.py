"""
tests/conftest.py — Pytest configuration and shared mock fixtures.
Allows running unit tests without an active Ollama instance or GPU.
"""

import sys
import os
import pytest
from unittest.mock import MagicMock

# Add project root to sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


@pytest.fixture
def mock_ollama_chat(monkeypatch):
    """Fixture to mock Ollama chat requests for offline testing."""
    def mock_chat(*args, **kwargs):
        return "Jawaban simulasi dari model mock untuk pengujian unit."
    
    monkeypatch.setattr("llm.ollama_client.chat_with_context", mock_chat)
    return mock_chat


@pytest.fixture
def sample_schedule_chunk():
    """Returns a realistic raw schedule chunk dictionary for testing."""
    return {
        "chunk_id": "1. TI - Jadwal Perkuliahan Genap 2025-2.rev.pdf_p1_semII_row0",
        "source": "1. TI - Jadwal Perkuliahan Genap 2025-2.rev.pdf",
        "page": 1,
        "prodi": "INF",
        "prodi_full": "Informatika (Teknik Informatika)",
        "semester": "II",
        "hari": "Senin",
        "mata_kuliah": "Interaksi Manusia dan Komputer",
        "dosen_names": "theresia herlina, s.kom., m.t.",
        "doc_type": "jadwal",
        "text": (
            "Entri jadwal kuliah resmi.\n"
            "Program studi: Informatika (kode: INF).\n"
            "Semester: II.\n"
            "Periode: Genap 2025/2026.\n"
            "Hari: Senin.\n"
            "Jam: 08.25 - 11.05.\n"
            "Mata kuliah: Interaksi Manusia dan Komputer.\n"
            "Kode mata kuliah: IS31713.\n"
            "SKS: 3.\n"
            "Kelas: A+B.\n"
            "Ruang: A306.\n"
            "Dosen pengampu tertulis: Theresia Herlina, S.Kom., M.T.\n"
            "Dosen Theresia Herlina, S.Kom., M.T mengajar mata kuliah Interaksi Manusia dan Komputer "
            "pada Program Studi Informatika semester II."
        ),
    }
