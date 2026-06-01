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

OLLAMA_BASE_URL  = "http://localhost:11434"
OLLAMA_API_URL   = f"{OLLAMA_BASE_URL}/v1/chat/completions"
DEFAULT_MODEL    = "qwen3:1.7b"

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
    "Jawab HANYA berdasarkan KONTEKS yang diberikan. Jangan mengarang.\n"
    "Jika jawaban tidak ada di konteks, katakan: "
    "'Maaf sobat, saya tidak memiliki informasi tersebut.'\n\n"
    "ATURAN WAJIB:\n"
    "1. Untuk pertanyaan DOSEN: cek baris 'Dosen pengampu tertulis:' di konteks. "
    "HANYA sebut dosen yang namanya TERTULIS di baris itu.\n"
    "2. JANGAN tebak dosen untuk EGAP — dosennya fleksibel.\n"
    "3. Untuk BIAYA kuliah umum: berikan contoh dari konteks, lalu minta jurusan spesifik.\n"
    "4. Jangan campur data antar jurusan atau semester.\n"
    "5. Tampilkan data apa adanya. Jangan bilang 'tidak mengajar di jurusan X' "
    "hanya karena data jurusan itu tidak ada.\n\n"
    "GAYA: Kasual, ramah, Bahasa Indonesia. Gunakan tabel Markdown untuk banyak entri.\n"
    "Jika pertanyaan dalam Bahasa Inggris, tetap jawab dalam Bahasa Indonesia."
)
