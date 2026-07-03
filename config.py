"""
config.py — Central configuration for Pradita University AI Chatbot
"""

import os
import sys

# Fix Windows console encoding for emoji globally
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
DATA_DIR      = os.path.join(BASE_DIR, "data")
CHROMA_DIR    = os.path.join(BASE_DIR, "chroma_db")

# OLLAMA_BASE_URL  = "http://localhost:11434"
# OLLAMA_API_URL   = f"{OLLAMA_BASE_URL}/v1/chat/completions"
# DEFAULT_MODEL    = "qwen3:1.7B"


OLLAMA_BASE_URL = "http://100.120.40.112:11434"
OLLAMA_API_URL = f"{OLLAMA_BASE_URL}/v1/chat/completions"

DEFAULT_MODEL = "gemma4:12b"

# ─── LLM Defaults ─────────────────────────────────────────────────────────────
DEFAULT_TEMPERATURE  = 0.4
DEFAULT_MAX_TOKENS   = 768
DEFAULT_TOP_K        = 40
DEFAULT_TOP_P        = 0.95

# ─── Embedding ────────────────────────────────────────────────────────────────
EMBEDDING_MODEL      = "intfloat/multilingual-e5-base"
CHROMA_COLLECTION    = "pradita_knowledge"

# ─── RAG ──────────────────────────────────────────────────────────────────────
CHUNK_SIZE       = 500        # characters per chunk
CHUNK_OVERLAP    = 100        # overlap between chunks
TOP_K_RETRIEVAL  = 6          # number of docs returned per query

# ─── System Prompt ────────────────────────────────────────────────────────────
SYSTEM_PROMPT = (
    "Kamu adalah Adita, asisten akademik AI Pradita University.\n"
    "Jawab SELALU berdasarkan KONTEKS yang diberikan di bawah.\n"
    "Jika jawaban tidak ada di konteks, katakan: "
    "'Maaf sobat, saya tidak memiliki informasi tersebut.'\n\n"
    "ATURAN WAJIB:\n"
    "1. JANGAN PERNAH diam atau memberikan respons kosong. Selalu tulis sesuatu.\n"
    "2. Untuk pertanyaan DOSEN/JADWAL: cek baris 'Dosen pengampu tertulis:' di konteks. "
    "HANYA sebut dosen yang namanya TERTULIS EKSPLISIT di baris itu.\n"
    "3. Untuk pertanyaan FASILITAS: baca konteks [Structured Facility Catalog] dan "
    "sebutkan semua fasilitas yang tercantum. Gunakan format bullet list atau tabel.\n"
    "4. Jangan campur data antar jurusan atau semester.\n"
    "5. Tampilkan data apa adanya dari konteks.\n"
    "6. JANGAN tebak dosen untuk EGAP — dosennya fleksibel.\n"
    "7. Untuk BIAYA kuliah umum: berikan contoh dari konteks, lalu minta jurusan spesifik.\n\n"
    "FORMAT OUTPUT:\n"
    "- Gunakan tabel Markdown untuk data jadwal (banyak baris).\n"
    "- Gunakan bullet list untuk fasilitas.\n"
    "- Singkat dan to the point, tapi lengkap.\n\n"
    "GAYA: Kasual, ramah, Bahasa Indonesia.\n"
    "Jika pertanyaan dalam Bahasa Inggris, tetap jawab dalam Bahasa Indonesia."
)


