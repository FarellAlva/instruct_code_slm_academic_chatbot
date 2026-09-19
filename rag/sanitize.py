"""
rag/sanitize.py — Comprehensive sanitization for user input, context chunks, and ingested documents.

Protects against:
- Unicode obfuscation (NFKC normalization, zero-width, bidi overrides, control characters)
- HTML/script/tag injection
- Direct and indirect prompt injection patterns (Indonesian & English)
- Long base64/hex payload smuggling
- Oversized input payloads
"""

import re
import unicodedata
import base64
from typing import Tuple, List, Dict, Any, Optional

# Invisible / Zero-width / Bidi control characters
_INVISIBLE_CHARS_PATTERN = re.compile(
    r"[\u200b\u200c\u200d\u200e\u200f\ufeff\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069\u206a-\u206f\x00-\x08\x0b\x0c\x0e-\x1f\x7f]"
)

# HTML tag / comment pattern
_HTML_TAG_PATTERN = re.compile(r"<[^>]+>")
_HTML_COMMENT_PATTERN = re.compile(r"<!--.*?-->", re.DOTALL)

# Delimiter collision protection: tag names used by Adita system
_SYSTEM_TAG_PATTERN = re.compile(
    r"</?(?:konteks_[0-9a-fA-F]+|pertanyaan_user_[0-9a-fA-F]+|keamanan|aturan_jawaban|dokumen|system|user|assistant)[^>]*>",
    re.IGNORECASE,
)

# Prompt Injection Patterns (ID + EN)
INJECTION_PATTERNS = [
    # English direct overrides
    r"\bignore\s+(?:all\s+)?(?:previous|prior|above)?\s*(?:instructions|rules|prompts?)\b",
    r"\bdisregard\s+(?:all\s+)?(?:previous|prior|above)?\s*(?:instructions|rules|prompts?)\b",
    r"\bforget\s+(?:all\s+)?(?:previous|prior|above)?\s*(?:instructions|rules|prompts?)\b",
    r"\byou\s+are\s+now\b",
    r"\bact\s+as\s+(?:a|an)?\b",
    r"\bpretend\s+to\s+be\b",
    r"\bdeveloper\s+mode\b",
    r"\bjailbreak\b",
    r"\b(?:system|sistem)\s+prompt\b",
    r"\brepeat\s+(?:the\s+)?(?:prompt|instructions|system|words\s+above)\b",
    r"\bwhat\s+(?:are|were)\s+your\s+(?:initial\s+)?instructions\b",
    r"\bprint\s+(?:your\s+)?(?:system\s+message|rules|prompt)\b",
    r"\bdo\s+anything\s+now\b",
    r"\bdan\s+mode\b",
    
    # Indonesian direct overrides
    r"\babaikan\s+(?:semua\s+)?(?:instruksi|perintah|aturan|petunjuk)\b",
    r"\blupakan\s+(?:semua\s+)?(?:instruksi|perintah|aturan|petunjuk)\b",
    r"\bjangan\s+(?:pernah\s+)?(?:ikuti|patuhi|tengok)\s+(?:instruksi|perintah|aturan)\b",
    r"\bkamu\s+sekarang\s+(?:adalah|menjadi|bebas)\b",
    r"\bbertindaklah\s+sebagai\b",
    r"\bberpura-pura(?:lah)?\s+menjadi\b",
    r"\bmode\s+(?:pengembang|developer|tanpa\s+batas|bebas|darurat)\b",
    r"\btampilkan\s+(?:(?:system|sistem)\s+prompt|perintah\s+sistem|instruksi\s+rahasia|aturan\s+sistem)\b",
    r"\bsebutkan\s+(?:kembali\s+)?(?:(?:system|sistem)\s+prompt|aturan\s+(?:aslimu|keamanan|sistem)|prompt\s+awal|security\s+canary)\b",
    r"\bapa\s+isi\s+(?:(?:system|sistem)\s+prompt|perintah\s+(?:sistem\s+)?awal|instruksi(?:mu)?)\b",
    r"\bbuka\s+(?:(?:system|sistem)\s+prompt|rahasiamu)\b",
    r"\bbocorkan\s+.*canary\b",
    r"\bADITA_SEC_TOKEN\b",
    
    # Smuggling / Delimiter spoofing
    r"\[\s*(?:SYSTEM|ASSISTANT|ADMIN|DEVELOPER|INSTRUKSI)\b",
    r"<\/?(?:system|instruction|prompt|admin)>",
]

_COMPILED_INJECTION_RE = [re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS]

# Base64 pattern (smuggling potential with padding support)
_BASE64_BLOB_PATTERN = re.compile(r"(?<![A-Za-z0-9+/])[A-Za-z0-9+/]{24,}={0,2}(?![A-Za-z0-9+/=])")


def normalize_unicode_nfkc(text: str) -> str:
    """Normalize text using Unicode NFKC to resolve visual confusable homoglyphs."""
    if not text:
        return ""
    return unicodedata.normalize("NFKC", text)


def strip_invisible_chars(text: str) -> str:
    """Strip zero-width spaces, bidi direction overrides, and control characters."""
    if not text:
        return ""
    return _INVISIBLE_CHARS_PATTERN.sub("", text)


def strip_html_and_tags(text: str) -> str:
    """Remove HTML comments, script/iframe tags, and general HTML tags."""
    if not text:
        return ""
    no_comments = _HTML_COMMENT_PATTERN.sub(" ", text)
    return _HTML_TAG_PATTERN.sub(" ", no_comments)


def escape_delimiter_tags(text: str) -> str:
    """Neutralize any attempt to inject or prematurely close system delimiter tags."""
    if not text:
        return ""
    return _SYSTEM_TAG_PATTERN.sub(lambda m: m.group(0).replace("<", "&lt;").replace(">", "&gt;"), text)


def detect_injection_patterns(text: str) -> Tuple[bool, List[str]]:
    """
    Check if text matches known prompt injection signatures.
    Returns (is_suspicious: bool, matched_patterns: list[str])
    """
    if not text:
        return False, []

    matched = []
    # Test compiled regex patterns
    for regex in _COMPILED_INJECTION_RE:
        if regex.search(text):
            matched.append(regex.pattern)

    # Test base64 blob smuggling
    b64_matches = _BASE64_BLOB_PATTERN.findall(text)
    for blob in b64_matches:
        try:
            pad = len(blob) % 4
            padded = blob + ("=" * (4 - pad) if pad else "")
            decoded = base64.b64decode(padded).decode("utf-8", errors="ignore")
            if any(regex.search(decoded) for regex in _COMPILED_INJECTION_RE):
                matched.append(f"base64_injection_payload:{blob[:16]}...")
        except Exception:
            pass

    return (len(matched) > 0), matched


def sanitize_user_input(
    user_input: str,
    max_chars: int = 500,
) -> Tuple[str, bool, List[str]]:
    """
    Full sanitization pipeline for user query:
    1. Unicode NFKC normalization
    2. Strip zero-width & bidi control characters
    3. Strip HTML / script tags
    4. Escape delimiter tags
    5. Length truncation
    6. Prompt injection pattern check

    Returns (cleaned_text, is_suspicious, matched_reasons)
    """
    if not user_input:
        return "", False, []

    # 1. Unicode NFKC
    clean = normalize_unicode_nfkc(user_input)

    # 2. Strip invisible chars
    clean = strip_invisible_chars(clean)

    # 3. Strip HTML
    clean = strip_html_and_tags(clean)

    # 4. Escape delimiter tags
    clean = escape_delimiter_tags(clean)

    # 5. Length bounding (default 500 chars)
    if len(clean) > max_chars:
        clean = clean[:max_chars].rsplit(" ", 1)[0]  # truncate cleanly at word boundary

    clean = re.sub(r"\s+", " ", clean).strip()

    # 6. Detection
    is_suspicious, reasons = detect_injection_patterns(clean)

    return clean, is_suspicious, reasons


def sanitize_context_chunk(chunk_text: str) -> Tuple[str, bool, List[str]]:
    """
    Sanitization applied to retrieved document chunks before injection into LLM context:
    - Normalizes Unicode
    - Strips invisible control characters
    - Escapes delimiter tags
    - Detects embedded indirect prompt injection

    Returns (sanitized_chunk_text, is_suspicious, reasons)
    """
    if not chunk_text:
        return "", False, []

    clean = normalize_unicode_nfkc(chunk_text)
    clean = strip_invisible_chars(clean)
    clean = escape_delimiter_tags(clean)

    is_suspicious, reasons = detect_injection_patterns(clean)
    return clean, is_suspicious, reasons
