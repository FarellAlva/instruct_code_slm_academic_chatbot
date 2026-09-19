"""
rag/chunker.py - Split extracted pages into overlapping text chunks.

Supports three chunking strategies:
  1. Standard sliding-window for generic PDFs
  2. Row-level schedule chunking for jadwal PDFs
  3. Section-aware chunking for scraped web text
"""

import os
import re
import sys
from typing import Any, Dict, List

# Ensure the root directory is on the path so we can import "config" from anywhere
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import CHUNK_OVERLAP, CHUNK_SIZE, SECTION_MAX_CHUNK_SIZE

# Add filenames (case-insensitive match) of PDFs that contain tables/jadwal.
SCHEDULE_FILES = [
    "jadwal",
    "schedule",
    "timetable",
    "kalender",
    "calendar",
    "roster",
    "mata_kuliah",
    "kurikulum",
]

PRODI_MAP = {
    "TI": "Informatika (Teknik Informatika)",
    "INF": "Informatika (Teknik Informatika)",
    "SI": "Sistem Informasi",
    "PAR": "Pariwisata (Perhotelan)",
    "PWK": "Perencanaan Wilayah dan Kota (Urban Planning)",
    "AR": "Arsitektur",
    "TS": "Teknik Sipil",
    "DKV": "Desain Komunikasi Visual",
    "DI": "Desain Interior",
    "SK": "Seni Kuliner",
    "MB": "Manajemen Bisnis",
    "MR": "Manajemen Bisnis / Retail",
    "AK": "Akuntansi",
    "F&B": "Food & Beverage",
    "MKDU": "Mata Kuliah Dasar Umum (MKDU)",
}

_ROW_RE = re.compile(
    r"^(\d+)\s+"                                        # NO
    r"(Senin|Selasa|Rabu|Kamis|Jumat|Sabtu)\s+"         # HARI
    r"(\d{2}\.\d{2}\s*-\s*\d{2}\.\d{2})\s+"             # JAM
    r"([IVX]+(?:\s*,\s*[IVX]+)*)\s+"                    # SMT
    r"([A-Z&]{2,4})\s+"                                 # PRODI
    r"(.+)$"                                            # REST
)
_ROW_START_RE = re.compile(
    r"^\d+\s+(?:Senin|Selasa|Rabu|Kamis|Jumat|Sabtu)\s+\d{2}\.\d{2}\s*-\s*\d{2}\.\d{2}\s+"
)
_KMK_RE = re.compile(r"^([A-Z]{2,4}\d{4,6})\s+")
_ROOM_RE = re.compile(
    r"\b(?:AG\d{2}|[A-Z]\d{2,3}|F\d{2}|Smart Class|Multi Hall|Lab(?:\s+[A-Za-z0-9&.-]+)*)\b"
)
_HEADER_PREFIXES = (
    "UNIVERSITAS PRADITA",
    "Jadwal Semester",
    "Program Studi",
    "NO Hari Jam SMT Prodi",
    "NO Hari Jam",
)


def _is_schedule_file(source: str) -> bool:
    """Check if a source filename matches one of the schedule patterns."""
    source_lower = source.lower()
    return any(keyword in source_lower for keyword in SCHEDULE_FILES)


def _chunk_sliding_window(
    text: str,
    source: str,
    page: int,
    chunk_size: int,
    chunk_overlap: int,
) -> List[Dict[str, Any]]:
    """
    Character-level sliding window chunking.
    Good for paragraphs, brochures, and general text PDFs.
    """
    chunks = []
    start = 0
    chunk_index = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk = text[start:end].strip()

        if chunk:
            chunk_id = f"{source}_p{page}_c{chunk_index}"
            chunks.append(
                {
                    "text": chunk,
                    "source": source,
                    "page": page,
                    "chunk_id": chunk_id,
                }
            )
        start += chunk_size - chunk_overlap
        chunk_index += 1

    return chunks


def _clean_inline_text(text: str) -> str:
    """Collapse repeated whitespace so wrapped PDF text stays parseable."""
    return re.sub(r"\s+", " ", text).strip(" .")


def _extract_schedule_period(text: str) -> str:
    match = re.search(r"Jadwal Semester\s+(.+?)\n", text, flags=re.IGNORECASE)
    if not match:
        return "Tidak disebutkan"
    return _clean_inline_text(match.group(1))


def _extract_prodi_name(source: str, text: str) -> str:
    match = re.search(r"Program Studi\s+([A-Za-z/& ]+)", text, flags=re.IGNORECASE)
    if match:
        return _clean_inline_text(match.group(1))

    code_match = re.search(r"(?:^\d+\.\s*|\b)([A-Z&]+)\b", source)
    if code_match and code_match.group(1) in PRODI_MAP:
        return PRODI_MAP[code_match.group(1)]

    return "Umum"


def _normalize_person_list(raw_dosen: str) -> List[str]:
    cleaned = _clean_inline_text(raw_dosen.replace(" ,", ","))
    if not cleaned or cleaned in {"-", "?", "TBA"}:
        return []

    candidates = re.split(r"\s*;\s*", cleaned)
    lecturers: List[str] = []
    for candidate in candidates:
        name = _clean_inline_text(candidate.rstrip(","))
        if not name:
            continue
        if name not in lecturers:
            lecturers.append(name)
    return lecturers


def _assemble_schedule_rows(text: str) -> List[str]:
    """Join extracted PDF lines so each returned string is one schedule row."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    rows: List[str] = []
    current: List[str] = []

    for line in lines:
        if any(line.startswith(prefix) for prefix in _HEADER_PREFIXES):
            continue

        if _ROW_START_RE.match(line):
            if current:
                rows.append("\n".join(current))
            current = [line]
        elif current:
            current.append(line)

    if current:
        rows.append("\n".join(current))

    return rows


def _split_room_and_notes(segment: str) -> tuple[str, str, str]:
    """
    Extract trailing room and optional note from a segment.

    Returns: (body_without_room, room, notes)
    """
    normalized = _clean_inline_text(segment)
    matches = list(_ROOM_RE.finditer(normalized))
    if not matches:
        return normalized, "Tidak tertulis", ""

    match = matches[-1]
    body = _clean_inline_text(normalized[:match.start()])
    room = _clean_inline_text(match.group(0))
    notes = _clean_inline_text(normalized[match.end():])
    return body, room, notes


def _build_schedule_chunk_text(
    *,
    period: str,
    prodi_full: str,
    prodi_code: str,
    semester: str,
    hari: str,
    jam: str,
    course_name: str,
    kmk: str,
    sks: str,
    kelas: str,
    room: str,
    notes: str,
    lecturers: List[str],
    is_egap: bool = False,
) -> str:
    lines = [
        "Entri jadwal kuliah resmi.",
        f"Program studi: {prodi_full} (kode: {prodi_code}).",
        f"Semester: {semester}.",
        f"Periode: {period}.",
        f"Hari: {hari}.",
        f"Jam: {jam}.",
        f"Mata kuliah: {course_name}.",
        f"Kode mata kuliah: {kmk}.",
        f"SKS: {sks}.",
        f"Kelas: {kelas}.",
        f"Ruang: {room}.",
    ]

    if lecturers:
        lines.append(f"Dosen pengampu tertulis: {'; '.join(lecturers)}.")
        lines.append(
            f"Dosen {', '.join(lecturers)} mengajar mata kuliah {course_name} "
            f"pada Program Studi {prodi_full} semester {semester}."
        )
    elif is_egap:
        lines.append(
            "Dosen pengampu: belum ditetapkan di jadwal ini karena EGAP bersifat fleksibel."
        )
    else:
        lines.append("Dosen pengampu: tidak tertulis pada entri jadwal ini.")

    if notes:
        lines.append(f"Catatan: {notes}.")

    return "\n".join(lines)


def _parse_row(line: str, prodi_full: str, period: str) -> Dict[str, Any] | None:
    """Parse a normalized schedule row into a retrieval-friendly chunk."""
    row_lines = [_clean_inline_text(part) for part in line.splitlines() if _clean_inline_text(part)]
    if not row_lines:
        return None

    base_line = row_lines[0]
    continuation_lines = row_lines[1:]

    match = _ROW_RE.match(base_line)
    if not match:
        return None

    hari = match.group(2)
    jam = _clean_inline_text(match.group(3))
    semester = _clean_inline_text(match.group(4))
    prodi_code = match.group(5)
    rest = match.group(6).strip()

    room = "Tidak tertulis"
    notes = ""

    if rest.startswith("EGAP"):
        parts = rest.split()
        if len(parts) >= 2:
            room = parts[1]
        if len(parts) >= 3:
            notes = _clean_inline_text(" ".join(parts[2:]))

        return {
            "semester": semester,
            "prodi_code": prodi_code,
            "prodi_full": prodi_full,
            "hari": hari,
            "jam": jam,
            "mata_kuliah": "EGAP (English for Academic Purposes)",
            "dosen_names": "",
            "text": _build_schedule_chunk_text(
                period=period,
                prodi_full=prodi_full,
                prodi_code=prodi_code,
                semester=semester,
                hari=hari,
                jam=jam,
                course_name="EGAP (English for Academic Purposes)",
                kmk="Tidak ada kode KMK pada entri ini",
                sks="Tidak tertulis",
                kelas="Tidak tertulis",
                room=room,
                notes=notes,
                lecturers=[],
                is_egap=True,
            ),
        }

    kmk = "Tidak tertulis"
    kmk_match = _KMK_RE.match(rest)
    if kmk_match:
        kmk = kmk_match.group(1)
        rest = rest[kmk_match.end():].strip()

    combined_rest = _clean_inline_text(" ".join([rest] + continuation_lines))
    rest, room, notes = _split_room_and_notes(combined_rest)

    detail_match = re.match(
        r"^(?P<course>.+?)\s+(?P<sks>\d)\s+(?P<kelas>[A-Z](?:\+[A-Z])*)(?:\s+(?P<dosen>.+))?$",
        rest,
    )

    if detail_match:
        course_name = _clean_inline_text(detail_match.group("course"))
        sks = detail_match.group("sks")
        kelas = detail_match.group("kelas")
        raw_dosen = detail_match.group("dosen") or ""
    else:
        course_name = _clean_inline_text(rest)
        sks = "Tidak tertulis"
        kelas = "Tidak tertulis"
        raw_dosen = ""

    lecturers = _normalize_person_list(raw_dosen)
    deduped_lecturers: List[str] = []
    for lecturer in lecturers:
        if lecturer not in deduped_lecturers:
            deduped_lecturers.append(lecturer)

    return {
        "semester": semester,
        "prodi_code": prodi_code,
        "prodi_full": prodi_full,
        "hari": hari,
        "jam": jam,
        "jam_mulai": jam.split("-")[0].strip() if "-" in jam else jam,
        "kode_mk": kmk,
        "ruang": room,
        "kelas": kelas,
        "periode": period,
        "needs_review": "false",
        "mata_kuliah": course_name,
        "dosen_names": ";".join(deduped_lecturers) if deduped_lecturers else "",
        "text": _build_schedule_chunk_text(
            period=period,
            prodi_full=prodi_full,
            prodi_code=prodi_code,
            semester=semester,
            hari=hari,
            jam=jam,
            course_name=course_name,
            kmk=kmk,
            sks=sks,
            kelas=kelas,
            room=room,
            notes=notes,
            lecturers=deduped_lecturers,
        ),
    }


def _chunk_table_aware(
    text: str,
    source: str,
    page: int,
) -> List[Dict[str, Any]]:
    """
    Row-level chunking for schedule PDFs.

    Each schedule row becomes one chunk so lecturer names cannot bleed into
    neighboring courses during retrieval.
    """
    prodi_name = _extract_prodi_name(source, text)
    period = _extract_schedule_period(text)
    rows = _assemble_schedule_rows(text)

    source_ver = "rev" if ".rev" in source.lower() else "non-rev"

    chunks: List[Dict[str, Any]] = []
    for chunk_index, row in enumerate(rows):
        parsed = _parse_row(row, prodi_name, period)
        if not parsed:
            continue

        semester_slug = re.sub(r"[^IVX]+", "-", parsed["semester"]).strip("-") or "UNKNOWN"
        chunks.append(
            {
                "text": parsed["text"],
                "source": source,
                "page": page,
                "chunk_id": f"{source}_p{page}_sem{semester_slug}_row{chunk_index}",
                # Rich metadata for pre-retrieval filtering (paper approach)
                "prodi": parsed.get("prodi_code", ""),
                "prodi_full": parsed.get("prodi_full", ""),
                "semester": parsed.get("semester", ""),
                "hari": parsed.get("hari", ""),
                "jam_mulai": parsed.get("jam_mulai", ""),
                "kode_mk": parsed.get("kode_mk", ""),
                "ruang": parsed.get("ruang", ""),
                "kelas": parsed.get("kelas", ""),
                "periode": period,
                "source_version": source_ver,
                "needs_review": parsed.get("needs_review", "false"),
                "mata_kuliah": parsed.get("mata_kuliah", ""),
                "dosen_names": parsed.get("dosen_names", ""),
                "doc_type": "jadwal",
            }
        )

    return chunks


def _chunk_by_section(
    text: str,
    source: str,
    page: int,
    max_chunk_size: int = SECTION_MAX_CHUNK_SIZE,
) -> List[Dict[str, Any]]:
    """
    Split text by markdown-style headers (## / ###) to keep sections intact.

    Good for web-scraped text that already has natural section boundaries.
    If an individual section exceeds max_chunk_size, cleanly splits by paragraphs
    or bullet points instead of slicing words mid-character.
    """
    sections = re.split(r"(?=^#{1,3}\s)", text, flags=re.MULTILINE)
    sections = [section.strip() for section in sections if section.strip()]

    def _split_oversized_section(sec_text: str) -> List[str]:
        """Split a large section cleanly on paragraph or line boundaries."""
        paragraphs = sec_text.split("\n\n")
        parts: List[str] = []
        buf = ""
        for p in paragraphs:
            p = p.strip()
            if not p:
                continue
            if len(buf) + len(p) + 2 <= max_chunk_size:
                buf = f"{buf}\n\n{p}" if buf else p
            else:
                if buf:
                    parts.append(buf.strip())
                    buf = ""
                if len(p) <= max_chunk_size:
                    buf = p
                else:
                    lines = p.split("\n")
                    line_buf = ""
                    for line in lines:
                        line = line.strip()
                        if not line:
                            continue
                        if len(line_buf) + len(line) + 1 <= max_chunk_size:
                            line_buf = f"{line_buf}\n{line}" if line_buf else line
                        else:
                            if line_buf:
                                parts.append(line_buf.strip())
                            line_buf = line
                    if line_buf:
                        buf = line_buf
        if buf:
            parts.append(buf.strip())
        return parts or [sec_text]

    chunks = []
    chunk_index = 0
    current_chunk = ""

    for section in sections:
        if len(current_chunk) + len(section) + 2 <= max_chunk_size:
            if current_chunk:
                current_chunk += "\n\n" + section
            else:
                current_chunk = section
        else:
            if current_chunk:
                chunk_id = f"{source}_p{page}_sec_c{chunk_index}"
                chunks.append(
                    {
                        "text": current_chunk.strip(),
                        "source": source,
                        "page": page,
                        "chunk_id": chunk_id,
                    }
                )
                chunk_index += 1
                current_chunk = ""

            if len(section) <= max_chunk_size:
                current_chunk = section
            else:
                sub_parts = _split_oversized_section(section)
                for part in sub_parts[:-1]:
                    chunk_id = f"{source}_p{page}_sec_c{chunk_index}"
                    chunks.append(
                        {
                            "text": part.strip(),
                            "source": source,
                            "page": page,
                            "chunk_id": chunk_id,
                        }
                    )
                    chunk_index += 1
                if sub_parts:
                    current_chunk = sub_parts[-1]

    if current_chunk:
        chunk_id = f"{source}_p{page}_sec_c{chunk_index}"
        chunks.append(
            {
                "text": current_chunk.strip(),
                "source": source,
                "page": page,
                "chunk_id": chunk_id,
            }
        )

    return chunks


def chunk_documents(
    documents: List[Dict[str, Any]],
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
) -> List[Dict[str, Any]]:
    """
    Smart chunking - pick the right strategy based on source file type.

    Strategy selection:
      - Schedule/jadwal files -> row-level table-aware chunking
      - Web-scraped text      -> section-aware chunking (keeps markdown sections intact)
      - Everything else       -> standard sliding window
    """
    chunks: List[Dict[str, Any]] = []

    for doc in documents:
        text = doc["text"]
        source = doc["source"]
        page = doc["page"]

        if _is_schedule_file(source):
            doc_chunks = _chunk_table_aware(text, source, page)
            strategy = "table-aware"
        elif source.startswith("web:"):
            doc_chunks = _chunk_by_section(
                text, source, page, max_chunk_size=SECTION_MAX_CHUNK_SIZE
            )
            strategy = "section-aware"
        else:
            doc_chunks = _chunk_sliding_window(
                text,
                source,
                page,
                chunk_size,
                chunk_overlap,
            )
            strategy = "sliding-window"

        chunks.extend(doc_chunks)

        if doc_chunks:
            print(
                f"[Chunker] {source} p.{page} -> "
                f"{len(doc_chunks)} chunks ({strategy})"
            )

    print(f"[Chunker] Total: {len(chunks)} chunks from {len(documents)} documents.")
    return chunks
