"""
rag/retriever.py - Query the ChromaDB collection and build a context string.

Enhanced following the Hendra Lijaya paper methodology:
  - Pre-retrieval metadata filtering via ChromaDB `where` clauses
  - Hybrid retrieval: dense vector search + metadata-boosted ranking
  - Cross-encoder reranking for final precision
  - Structured context injection for reduced hallucination

Performance optimizations:
  - Singleton ChromaDB collection (store.py)
  - Lighter reranker model (MiniLM-L-6-v2 vs bge-reranker-v2-m3)
  - Reduced pool size (POOL_SIZE_FACTOR from config)
  - Cached collection.count() per-request
  - Timing instrumentation for profiling
"""

import re
import time
from typing import Any, Dict, List, Optional, Tuple

from config import (
    TOP_K_RETRIEVAL,
    USE_RERANKER,
    RERANKER_MODEL,
    POOL_SIZE_FACTOR,
    MAX_CONTEXT_TOKENS,
    estimate_tokens,
)
from .store import get_chroma_collection

_RERANKER_MODEL = None
_STOP_WORDS = {
    "siapa", "itu", "apa", "apakah", "ada", "di", "ke", "dari", "yang", "dan",
    "untuk", "jadwal", "berikan", "saya", "tolong", "bisa", "adalah", "ini",
    "beliau", "ngajar", "mengajar", "ampu", "mengampu", "mata", "kuliah", "semester",
    "prodi", "jurusan", "kelas", "ruang", "jam", "hari", "berapa", "apa saja",
    "bagaimana", "dengan", "tentang", "pak", "bu", "bapak", "ibu", "ajarkan", "ajar",
    "saja", "dosen", "oleh", "diajarkan", "diampu", "diajarin", "diajar",
    "matakuliah", "matkul", "kode", "kapan", "dimana",
    # Location / institution words that are NOT names
    "mana", "lokasi", "kampus", "universitas", "university", "pradita",
    "gedung", "ruangan", "alamat", "kantor", "fakultas", "program", "studi",
    "indonesia", "jakarta", "tangerang", "banten", "serpong", "gading",
    "tower", "building", "blok", "jalan", "scientia", "summarecon",
    # Common question words
    "apa", "siapa", "kapan", "dimana", "bagaimana", "berapa", "mengapa",
    "where", "what", "how", "when", "who", "does", "is", "are", "the",
    # Academic terms
    "informatika", "sistem", "informasi", "teknik", "desain", "manajemen",
    "akuntansi", "arsitektur", "pariwisata", "kuliner", "interior",
}

PRODI_ALIASES = {
    "teknik informatika": "INF", "informatika": "INF",
    "sistem informasi": "SI",
    "pariwisata": "PAR", "perhotelan": "PAR",
    "perencanaan wilayah": "PWK",
    "arsitektur": "AR",
    "teknik sipil": "TS",
    "desain komunikasi visual": "DKV",
    "desain interior": "DI",
    "seni kuliner": "SK",
    "manajemen bisnis": "MB", "manajemen": "MB",
    "akuntansi": "AK",
    "food beverage": "F&B",
    "mkdu": "MKDU",
}

# Short aliases that require word-boundary matching (regex \b)
_PRODI_SHORT_ALIASES = {
    "ti": "INF", "inf": "INF",
    "si": "SI",
    "par": "PAR",
    "pwk": "PWK",
    "ar": "AR",
    "ts": "TS",
    "dkv": "DKV",
    "di": "DI",
    "sk": "SK",
    "mb": "MB",
    "ak": "AK",
    "f&b": "F&B", "fnb": "F&B",
}

ROMAN_MAP = {"1": "I", "2": "II", "3": "III", "4": "IV", "5": "V",
             "6": "VI", "7": "VII", "8": "VIII"}

DAY_NAMES = {"senin", "selasa", "rabu", "kamis", "jumat", "sabtu"}


def get_reranker():
    global _RERANKER_MODEL
    if _RERANKER_MODEL is None:
        from sentence_transformers import CrossEncoder
        import torch
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"[Reranker] Loading CrossEncoder: {RERANKER_MODEL} ({device.upper()})...")
        _RERANKER_MODEL = CrossEncoder(
            RERANKER_MODEL,
            max_length=512,
            device=device,
        )
        print(f"[Reranker] ✅ CrossEncoder ready on {device.upper()}.")
    return _RERANKER_MODEL


def _normalize_text(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


# ─── Bilingual Query Expansion ────────────────────────────────────────────────
# Maps common English question keywords → Indonesian equivalents.
# Used to boost retrieval when the user asks in English but data is in Indonesian.

_EN_TO_ID_TERMS: dict[str, str] = {
    # Location / campus
    "located":     "lokasi kampus alamat",
    "location":    "lokasi kampus alamat",
    "address":     "alamat lokasi kampus",
    "where":       "dimana lokasi",
    # Tuition / costs
    "tuition":     "biaya kuliah uang kuliah",
    "fee":         "biaya uang kuliah",
    "cost":        "biaya harga",
    "price":       "harga biaya kuliah",
    "payment":     "pembayaran biaya cicilan",
    # Schedule
    "schedule":    "jadwal perkuliahan",
    "class":       "kelas jadwal kuliah",
    "lecture":     "perkuliahan jadwal",
    # Facilities
    "facility":    "fasilitas sarana prasarana",
    "facilities":  "fasilitas sarana prasarana",
    "dormitory":   "asrama tempat tinggal kos",
    "housing":     "tempat tinggal asrama kos hunian",
    "boarding":    "asrama kos tempat tinggal",
    # Programs / majors
    "major":       "jurusan program studi prodi",
    "program":     "program studi jurusan prodi",
    "department":  "jurusan program studi",
    "faculty":     "fakultas jurusan",
    # Lecturer / staff
    "lecturer":    "dosen pengajar",
    "teacher":     "dosen pengajar",
    "professor":   "dosen profesor",
    # Scholarship
    "scholarship": "beasiswa bantuan dana",
    # Enrollment / registration
    "register":    "daftar pendaftaran",
    "enrollment":  "pendaftaran mahasiswa baru",
    "admission":   "penerimaan mahasiswa baru pendaftaran",
    # Contact
    "contact":     "kontak email telepon",
    "email":       "email kontak",
    # General
    "university":  "universitas perguruan tinggi",
    "campus":      "kampus universitas",
    "pradita":     "pradita university",
    "about":       "tentang informasi",
    "what":        "apa",
    "how":         "bagaimana cara",
    "when":        "kapan",
    "who":         "siapa",
}


def _expand_query(query: str) -> str:
    """
    Expand the query with Indonesian equivalents if English keywords are detected.
    Returns the enriched query string used ONLY for embedding/retrieval.
    The original query is preserved for the LLM.
    """
    lowered = query.lower()
    # Detect if query is likely English (has common English question words or terms)
    en_indicators = {"where", "what", "how", "when", "who", "does", "is", "are",
                     "located", "location", "tuition", "fee", "cost", "schedule",
                     "facility", "facilities", "major", "program", "scholarship",
                     "register", "enrollment", "admission", "campus", "lecturer",
                     "about", "contact", "dormitory", "housing", "boarding"}

    tokens = set(re.findall(r"[a-z]+", lowered))
    matches = tokens & en_indicators
    if not matches:
        return query  # Already Indonesian, no expansion needed

    extra_terms = []
    for token, translation in _EN_TO_ID_TERMS.items():
        if token in lowered:
            extra_terms.append(translation)

    if extra_terms:
        expanded = f"{query} {' '.join(extra_terms)}"
        print(f"[Retriever] 🌐 Query expanded (len={len(query)}) → added: {extra_terms}")
        return expanded

    return query


# ─── Query Intent Extraction ──────────────────────────────────────────────────

def _extract_person_name_query(query: str) -> str:
    """Extract lecturer name from the query, if present."""
    lowered = query.lower()
    if not any(token in lowered for token in ("dosen", "ajar", "ampu", "beliau", "ngajar")):
        return ""

    tokens = re.findall(r"[A-Za-z][A-Za-z'.-]*", query)
    filtered = [t for t in tokens if t.lower() not in _STOP_WORDS]
    if len(filtered) < 2:
        return ""

    best_window = ""
    for size in range(min(5, len(filtered)), 1, -1):
        for start in range(0, len(filtered) - size + 1):
            window = filtered[start:start + size]
            capitalized = sum(1 for token in window if token[:1].isupper())
            if capitalized >= 2:
                best_window = " ".join(window)
                break
        if best_window:
            break

    return best_window or ""


def _extract_prodi_filter(query: str) -> Optional[str]:
    """Extract prodi code from query for metadata filtering."""
    lowered = query.lower()
    
    # Check if this query is likely about schedules
    schedule_keywords = ["jadwal", "kelas", "ruang", "mata kuliah", "matkul", "semester", "hari", "jam"]
    if not any(kw in lowered for kw in schedule_keywords):
        return None

    # First try long aliases (substring match is safe for multi-word)
    for alias, code in sorted(PRODI_ALIASES.items(), key=lambda x: -len(x[0])):
        if alias in lowered:
            return code
    # Then try short aliases with word boundary to avoid false positives
    for alias, code in _PRODI_SHORT_ALIASES.items():
        if re.search(r'\bprodi\s+' + re.escape(alias) + r'\b', lowered):
            return code
        if re.search(r'\bjurusan\s+' + re.escape(alias) + r'\b', lowered):
            return code
    return None


def _extract_semester_filter(query: str) -> Optional[str]:
    """Extract semester (roman numeral) from query."""
    lowered = query.lower()
    for m in re.finditer(r"\bsemester\s+([ivx]+|\d+)\b", lowered):
        token = m.group(1).upper()
        if token.isdigit():
            return ROMAN_MAP.get(token, token)
        return token
    return None


def _extract_day_filter(query: str) -> Optional[str]:
    """Extract day name from query."""
    lowered = query.lower()
    for day in DAY_NAMES:
        if day in lowered:
            return day.capitalize()
    return None


# ─── Pre-Retrieval Filtering (Paper Approach) ─────────────────────────────────

def _build_filters(
    person_query: str,
    prodi_code: Optional[str],
    semester: Optional[str],
    day: Optional[str],
) -> tuple[Optional[Dict], Optional[Dict]]:
    """
    Build ChromaDB `where` (metadata) and `where_document` (text) filters.

    ChromaDB does NOT support $contains on metadata strings, so:
    - prodi, semester, hari → metadata `where` with $eq
    - person name → `where_document` with $contains (searches doc text)
    """
    where_conditions = []
    where_document = None

    if prodi_code:
        where_conditions.append({"prodi": {"$eq": prodi_code}})

    if semester:
        where_conditions.append({"semester": {"$eq": semester}})

    if day:
        where_conditions.append({"hari": {"$eq": day}})

    # Person name → search document text directly
    if person_query:
        # Use the most distinctive name part for text search
        name_parts = _normalize_text(person_query).split()
        if name_parts:
            best_part = max(name_parts, key=len)
            if len(best_part) >= 3:
                where_document = {"$contains": best_part}

    where_filter = None
    if len(where_conditions) == 1:
        where_filter = where_conditions[0]
    elif len(where_conditions) > 1:
        where_filter = {"$and": where_conditions}

    return where_filter, where_document


# ─── Lecturer Matching (kept for post-retrieval validation) ────────────────────

def _extract_lecturers_from_chunk(text: str) -> List[str]:
    for line in text.splitlines():
        if line.startswith("Dosen pengampu tertulis:"):
            value = line.split(":", 1)[1].strip().rstrip(".")
            return [name.strip() for name in value.split(";") if name.strip()]
    return []


def _chunk_matches_person_query(chunk_text: str, person_query: str) -> bool:
    if not person_query:
        return True

    target = _normalize_text(person_query)
    lecturers = _extract_lecturers_from_chunk(chunk_text)
    if not lecturers:
        return False

    for lecturer in lecturers:
        normalized_lecturer = _normalize_text(lecturer)
        if target in normalized_lecturer or normalized_lecturer in target:
            return True

    # Fallback: check individual name parts
    target_parts = target.split()
    for lecturer in lecturers:
        normalized_lecturer = _normalize_text(lecturer)
        matches = sum(1 for part in target_parts if part in normalized_lecturer)
        if matches >= 2:
            return True

    return False


# ─── Main Retrieval Function ──────────────────────────────────────────────────

def retrieve_context(
    query: str,
    top_k: int = TOP_K_RETRIEVAL,
    collection=None,
) -> Dict[str, Any]:
    """
    Retrieve the top-k most relevant chunks for query.

    Pipeline (following paper methodology):
      1. Extract query intent (person, prodi, semester, day)
      2. Pre-retrieval filtering via ChromaDB `where` clause
      3. Dense vector similarity search
      4. Cross-encoder reranking
      5. Build structured context string

    Returns:
      {
        "context":  str,
        "sources":  List[str],
        "chunks":   List[Dict],
      }
    """
    t_start = time.perf_counter()

    if collection is None:
        collection = get_chroma_collection()

    # Cache count once per call to avoid two round-trips to ChromaDB
    doc_count = collection.count()
    if doc_count == 0:
        return {"context": "", "sources": [], "chunks": []}

    # Step 1: Extract query intents
    t1 = time.perf_counter()
    person_query = _extract_person_name_query(query)
    prodi_code = _extract_prodi_filter(query)
    semester = _extract_semester_filter(query)
    day = _extract_day_filter(query)

    # Step 1b: Expand query with Indonesian equivalents for cross-lingual retrieval
    retrieval_query = _expand_query(query)

    print(f"[Retriever] Intent ({(time.perf_counter()-t1)*1000:.0f}ms) — "
          f"person: {person_query or '-'}, "
          f"prodi: {prodi_code or '-'}, sem: {semester or '-'}, day: {day or '-'}")

    # Step 2: Pre-retrieval filtering
    where_filter, where_doc_filter = _build_filters(person_query, prodi_code, semester, day)

    # Step 3: Dense vector search with optional metadata + document filters
    pool_size = min(max(top_k * POOL_SIZE_FACTOR, 10), doc_count)

    has_filters = where_filter is not None or where_doc_filter is not None

    t2 = time.perf_counter()
    try:
        results = collection.query(
            query_texts=[retrieval_query],   # expanded query for better cross-lingual retrieval
            n_results=pool_size,
            include=["documents", "metadatas", "distances"],
            where=where_filter,
            where_document=where_doc_filter,
        )
    except Exception as e:
        # If filtered query returns nothing or errors, fallback to unfiltered
        print(f"[Retriever] ⚠ Filtered query failed ({e}), falling back to unfiltered")
        has_filters = False
        results = collection.query(
            query_texts=[retrieval_query],
            n_results=pool_size,
            include=["documents", "metadatas", "distances"],
        )
    print(f"[Retriever] Dense search ({(time.perf_counter()-t2)*1000:.0f}ms)")

    docs = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    if not docs:
        # Filtered query returned empty, retry without filter
        if has_filters:
            print("[Retriever] ⚠ No results with filter, retrying unfiltered")
            t_retry = time.perf_counter()
            results = collection.query(
                query_texts=[query],
                n_results=pool_size,
                include=["documents", "metadatas", "distances"],
            )
            docs = results["documents"][0]
            metadatas = results["metadatas"][0]
            distances = results["distances"][0]
            print(f"[Retriever] Fallback search ({(time.perf_counter()-t_retry)*1000:.0f}ms)")

    chunks: List[Dict[str, Any]] = []
    seen_texts = set()
    for doc, meta, dist in zip(docs, metadatas, distances):
        if doc in seen_texts:
            continue
        seen_texts.add(doc)
        meta = meta or {}
        chunks.append({
            "text": doc,
            "source": meta.get("source", "unknown"),
            "page": meta.get("page", 0),
            "distance": dist,
            "meta": meta,  # Keep full metadata for downstream use
        })

    print(f"[Retriever] Dense search returned {len(chunks)} unique chunks"
          + (f" (filtered: {where_filter})" if where_filter else " (unfiltered)"))

    # Step 3b: Post-retrieval person validation
    if person_query:
        matched = [c for c in chunks if _chunk_matches_person_query(c["text"], person_query)]
        if matched:
            chunks = matched
            print(f"[Retriever] Person filter kept {len(chunks)} chunks for [ANON]")

    # Step 4: Cross-encoder reranking (only if enabled in config)
    if chunks and USE_RERANKER:
        t3 = time.perf_counter()
        reranker = get_reranker()
        pairs = [[query, chunk["text"]] for chunk in chunks]
        # batch_size tuned for GPU throughput; convert_to_numpy avoids extra tensor overhead
        scores = reranker.predict(pairs, batch_size=32, convert_to_numpy=True)
        print(f"[Retriever] Reranking {len(pairs)} pairs ({(time.perf_counter()-t3)*1000:.0f}ms)")

        for i, chunk in enumerate(chunks):
            chunk["rerank_score"] = float(scores[i])

        # Sort by rerank score (primary), with person-match bonus
        chunks.sort(
            key=lambda item: (
                1 if _chunk_matches_person_query(item["text"], person_query) else 0,
                item["rerank_score"],
            ),
            reverse=True,
        )
    elif chunks and not USE_RERANKER:
        # No reranker: sort by cosine distance (lower = more similar)
        chunks.sort(key=lambda item: item["distance"])

    # Take more results for person queries (they may teach many courses)
    result_limit = top_k
    if person_query:
        result_limit = min(max(top_k, 10), len(chunks))
    chunks = chunks[:result_limit]

    # Step 5: Build structured context string adhering to token budget
    context, chunks = _build_structured_context(chunks, person_query)
    sources = list({chunk["source"] for chunk in chunks})

    print(f"[Retriever] ✅ Total retrieval time: {(time.perf_counter()-t_start)*1000:.0f}ms "
          f"| chunks returned: {len(chunks)}")

    return {"context": context, "sources": sources, "chunks": chunks}


def _build_structured_context(
    chunks: List[Dict[str, Any]],
    person_query: str,
    max_context_tokens: int = MAX_CONTEXT_TOKENS,
) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Build a structured context string that makes it easy for the LLM
    to extract information without hallucinating.

    Token budget: Chunks are added in rank order until max_context_tokens
    is reached. Lower-ranked chunks that exceed budget are cleanly omitted
    as whole chunks without breaking mid-schedule lines.
    """
    if not chunks:
        return "", []

    context_parts = []
    included_chunks = []
    current_tokens = 0

    if person_query:
        instruction = (
            f"[INSTRUKSI KONTEKS] Berikut adalah data jadwal yang ditemukan. "
            f"HANYA gunakan informasi yang TERTULIS EKSPLISIT di bawah. "
            f"Fokus pencarian: dosen '{person_query}'."
        )
        context_parts.append(instruction)
        current_tokens += estimate_tokens(instruction)

    from rag.sanitize import sanitize_context_chunk

    for idx, chunk in enumerate(chunks, 1):
        meta = chunk.get("meta", {})
        if meta.get("suspicious") in (True, "true"):
            print(f"[SECURITY] Omitting chunk marked suspicious from context: {chunk.get('source')}")
            continue

        raw_chunk_text = chunk.get("text", "")
        clean_text, is_suspicious, reasons = sanitize_context_chunk(raw_chunk_text)
        if is_suspicious:
            print(f"[SECURITY] Omitting chunk with injection pattern {reasons} from context: {chunk.get('source')}")
            continue

        header_parts = [f"Dokumen #{idx}"]

        # Add metadata summary if available
        if meta.get("doc_type") == "jadwal":
            if meta.get("prodi_full"):
                header_parts.append(f"Prodi: {meta['prodi_full']}")
            if meta.get("semester"):
                header_parts.append(f"Sem: {meta['semester']}")
            if meta.get("hari"):
                header_parts.append(f"Hari: {meta['hari']}")
        else:
            header_parts.append(f"Source: {chunk.get('source', 'unknown')}")

        score_info = ""
        if "rerank_score" in chunk:
            score_info = f" | Relevance: {chunk['rerank_score']:.3f}"

        doc_str = f"[{' | '.join(header_parts)}{score_info}]\n{clean_text}"
        doc_tokens = estimate_tokens(doc_str) + 4  # delimiter budget

        if current_tokens + doc_tokens > max_context_tokens:
            omitted_count = len(chunks) - len(included_chunks)
            print(
                f"[Retriever] ⚠️ Context budget reached ({current_tokens}/{max_context_tokens} tokens). "
                f"Omitted {omitted_count} lower-ranked chunks cleanly without mid-chunk truncation."
            )
            break

        context_parts.append(doc_str)
        # Update chunk text in memory with clean text
        chunk_copy = dict(chunk)
        chunk_copy["text"] = clean_text
        included_chunks.append(chunk_copy)
        current_tokens += doc_tokens

    return "\n\n---\n\n".join(context_parts), included_chunks
