"""
rag/entity_index.py — In-memory entity index built from schedule metadata.

Enables fast, deterministic, positive-only lookups for:
1. "Dosen pengampu mata kuliah" (intent: course instructor)
2. "Jadwal dosen" (intent: lecturer schedule)
3. "Jadwal mata kuliah / kode MK"

GOLDEN RULE:
The bypass must ONLY produce POSITIVE answers from structured data.
Under no circumstance may it produce a refusal. If no definitive match
is found, it returns None, allowing the RAG/LLM pipeline to handle it.
"""

import re
import html
from typing import Dict, List, Optional, Any, Tuple

_TITLES_PATTERN = re.compile(
    r"\b(?:dr|dra|drs|prof|eng|ph\.?d|s\.?kom|m\.?t|m\.?kom|s\.?e|m\.?m|s\.?t|s\.?pd|m\.?pd|"
    r"m\.?par|m\.?sn|s\.?si|m\.?eng|b\.?a|ak|bkp|cbc|a-cpa|mt\.bnsp|m\.?hum|m\.?tech|m\.?hsc)\b\.?",
    re.IGNORECASE,
)

_COURSE_STOP_WORDS = {
    "dan", "&", "mata", "kuliah", "matkul", "program", "studi", "prodi",
    "kelas", "jadwal", "semester", "hari", "jam", "ruang", "kode", "sks",
}

_LECTURER_QUERY_INTENT_WORDS = {
    "siapa", "dosen", "pengampu", "mengampu", "diajar", "ajar", "ngajar",
    "guru", "pengajar", "diajarin", "siapakah",
}

_SCHEDULE_QUERY_INTENT_WORDS = {
    "jadwal", "kapan", "hari", "jam", "waktu", "ruang", "ruangan", "di mana",
    "dimana", "mata kuliah apa", "ngajar apa", "mengajar apa", "mengajar",
}

_DAY_ORDER = {"Senin": 0, "Selasa": 1, "Rabu": 2, "Kamis": 3, "Jumat": 4, "Sabtu": 5}
_ROMAN_TO_INT = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7, "VIII": 8}


def normalize_title(name: str) -> str:
    """Normalize lecturer name by stripping academic titles and punctuation."""
    cleaned = _TITLES_PATTERN.sub("", name.lower())
    cleaned = re.sub(r"[^a-z0-9\s]+", " ", cleaned)
    return " ".join(cleaned.split())


def normalize_course_name(course: str) -> str:
    """Normalize course name for fuzzy entity matching (ignoring punctuation and stopwords like 'dan')."""
    cleaned = re.sub(r"[^a-z0-9\s]+", " ", course.lower())
    words = [w for w in cleaned.split() if w not in _COURSE_STOP_WORDS]
    return " ".join(words)


def normalize_lookup(text: str) -> str:
    """General alphanumeric normalization."""
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def parse_schedule_text(chunk_text: str) -> Optional[Dict[str, Any]]:
    """Parse structured schedule fields from raw chunk text."""
    if "Entri jadwal kuliah resmi." not in chunk_text:
        return None

    entry: Dict[str, Any] = {}
    for line in chunk_text.splitlines():
        clean = line.strip()
        if clean.startswith("Program studi:"):
            entry["prodi_full"] = clean.split(":", 1)[1].strip().rstrip(".")
        elif clean.startswith("Semester:"):
            entry["semester"] = clean.split(":", 1)[1].strip().rstrip(".")
        elif clean.startswith("Periode:"):
            entry["periode"] = clean.split(":", 1)[1].strip().rstrip(".")
        elif clean.startswith("Hari:"):
            entry["hari"] = clean.split(":", 1)[1].strip().rstrip(".")
        elif clean.startswith("Jam:"):
            entry["jam"] = clean.split(":", 1)[1].strip().rstrip(".")
        elif clean.startswith("Mata kuliah:"):
            entry["mata_kuliah"] = clean.split(":", 1)[1].strip().rstrip(".")
        elif clean.startswith("Kode mata kuliah:"):
            entry["kode_mk"] = clean.split(":", 1)[1].strip().rstrip(".")
        elif clean.startswith("SKS:"):
            entry["sks"] = clean.split(":", 1)[1].strip().rstrip(".")
        elif clean.startswith("Kelas:"):
            entry["kelas"] = clean.split(":", 1)[1].strip().rstrip(".")
        elif clean.startswith("Ruang:"):
            entry["ruang"] = clean.split(":", 1)[1].strip().rstrip(".")
        elif clean.startswith("Dosen pengampu tertulis:"):
            raw = clean.split(":", 1)[1].strip().rstrip(".")
            dosen_list = []
            for name in raw.split(";"):
                c_name = re.sub(
                    r"\b(?:AG\d{2}|[A-Z]\d{2,3}|F\d{2}|Smart Class|Multi Hall|Lab(?:\s+[A-Za-z0-9&.-]+)*)\b.*$",
                    "",
                    name,
                    flags=re.IGNORECASE,
                ).strip(" .,;")
                if c_name and len(c_name.split()) >= 2:
                    dosen_list.append(c_name)
            entry["dosen_list"] = dosen_list

    if entry.get("mata_kuliah"):
        return entry
    return None


class EntityIndex:
    """
    Singleton entity index containing courses, lecturers, course codes, and rooms.
    """

    def __init__(self):
        self.courses: Dict[str, List[Dict[str, Any]]] = {}
        self.lecturers: Dict[str, List[Dict[str, Any]]] = {}
        self.course_codes: Dict[str, List[Dict[str, Any]]] = {}
        self.rooms: Dict[str, List[Dict[str, Any]]] = {}
        self.all_entries: List[Dict[str, Any]] = []
        self._is_indexed = False

    def build_from_collection(self, collection) -> None:
        """Build entity index from ChromaDB collection documents and metadatas."""
        try:
            data = collection.get(include=["metadatas", "documents"])
        except Exception as e:
            print(f"[EntityIndex] ❌ Failed to fetch collection: {e}")
            return

        documents = data.get("documents", [])
        metadatas = data.get("metadatas", [])

        self.courses.clear()
        self.lecturers.clear()
        self.course_codes.clear()
        self.rooms.clear()
        self.all_entries.clear()

        for doc, meta in zip(documents, metadatas):
            if not meta or meta.get("doc_type") != "jadwal":
                continue

            parsed = parse_schedule_text(doc)
            if not parsed:
                continue

            parsed["source"] = meta.get("source", "unknown")
            parsed["page"] = meta.get("page", 1)
            parsed["prodi"] = meta.get("prodi", "")
            if not parsed.get("prodi_full") and meta.get("prodi_full"):
                parsed["prodi_full"] = meta["prodi_full"]

            self.all_entries.append(parsed)

            # Index course
            mk = parsed.get("mata_kuliah", "")
            if mk:
                norm_mk = normalize_course_name(mk)
                if norm_mk:
                    self.courses.setdefault(norm_mk, []).append(parsed)

            # Index course code
            kmk = parsed.get("kode_mk", "")
            if kmk:
                norm_kmk = normalize_lookup(kmk)
                if norm_kmk:
                    self.course_codes.setdefault(norm_kmk, []).append(parsed)

            # Index lecturers
            for d in parsed.get("dosen_list", []):
                norm_d = normalize_title(d)
                if norm_d and len(norm_d.split()) >= 2:
                    self.lecturers.setdefault(norm_d, []).append(parsed)

            # Index room
            ruang = parsed.get("ruang", "")
            if ruang:
                norm_r = normalize_lookup(ruang)
                if norm_r:
                    self.rooms.setdefault(norm_r, []).append(parsed)

        self._is_indexed = True
        print(f"[EntityIndex] ✅ Indexed {len(self.courses)} courses, "
              f"{len(self.lecturers)} lecturers, {len(self.course_codes)} codes.")

    def match_course(self, query: str) -> Optional[Tuple[str, List[Dict[str, Any]]]]:
        """
        Check if query mentions any known course name.
        Returns (matched_normalized_name, entries) or None.
        Matches longest course name first to prevent partial substring collisions.
        """
        norm_q = normalize_course_name(query)
        best_match = None
        best_len = 0

        for norm_course, entries in self.courses.items():
            if len(norm_course) < 4:
                continue
            # Exact boundary or substring match
            if norm_course in norm_q:
                if len(norm_course) > best_len:
                    best_match = (norm_course, entries)
                    best_len = len(norm_course)

        return best_match

    def match_lecturer(self, query: str) -> Optional[Tuple[str, List[Dict[str, Any]]]]:
        """
        Check if query mentions any known lecturer name.
        Returns (matched_lecturer_name, entries) or None.
        Matches longest lecturer name first.
        """
        norm_q = normalize_title(query)
        best_match = None
        best_len = 0

        for norm_lec, entries in self.lecturers.items():
            if len(norm_lec) < 5:
                continue
            # Lecturer matching requires all constituent tokens of the normalized name
            lec_tokens = norm_lec.split()
            if all(token in norm_q for token in lec_tokens):
                if len(norm_lec) > best_len:
                    best_match = (norm_lec, entries)
                    best_len = len(norm_lec)

        return best_match

    def answer_direct_query(self, query: str) -> Optional[str]:
        """
        Attempt to produce a POSITIVE structured answer for course instructor or lecturer schedule.
        RETURNS None if no positive answer can be guaranteed, leaving it to RAG + LLM.
        """
        if not self._is_indexed:
            return None

        q_lower = query.lower()
        has_instructor_intent = any(w in q_lower for w in _LECTURER_QUERY_INTENT_WORDS)
        has_schedule_intent = any(w in q_lower for w in _SCHEDULE_QUERY_INTENT_WORDS)

        # 1. Check Course Match
        course_match = self.match_course(query)
        if course_match:
            norm_course, entries = course_match
            # If the user asks who teaches the course (or general course instructor question)
            if has_instructor_intent:
                # Find entries with explicit lecturers
                entries_with_lecturers = [e for e in entries if e.get("dosen_list")]
                if entries_with_lecturers:
                    # Positive answer!
                    first_mk = entries_with_lecturers[0].get("mata_kuliah", norm_course.title())
                    
                    # Deduplicate entries by prodi, class, and lecturer
                    seen = set()
                    table_rows = []
                    for e in entries_with_lecturers:
                        lecturers_str = ", ".join(e["dosen_list"])
                        key = (e.get("prodi_full", ""), e.get("semester", ""), e.get("kelas", ""), lecturers_str)
                        if key in seen:
                            continue
                        seen.add(key)
                        table_rows.append(
                            f"| {e.get('prodi_full', e.get('prodi', '-'))} | "
                            f"Semester {e.get('semester', '-')} | "
                            f"{e.get('kelas', '-')} | "
                            f"{e.get('hari', '-')} {e.get('jam', '')} | "
                            f"{e.get('ruang', '-')} | "
                            f"**{lecturers_str}** |"
                        )

                    header = f"Berikut dosen pengampu resmi untuk mata kuliah **{first_mk}** berdasarkan jadwal perkuliahan:"
                    table_header = [
                        "| Program Studi | Semester | Kelas | Hari & Jam | Ruang | Dosen Pengampu |",
                        "| :--- | :--- | :--- | :--- | :--- | :--- |",
                    ]
                    return f"{header}\n\n" + "\n".join(table_header + table_rows)

        # 2. Check Lecturer Match
        lecturer_match = self.match_lecturer(query)
        if lecturer_match:
            norm_lec, entries = lecturer_match
            if has_schedule_intent or has_instructor_intent:
                # Filter entries explicitly matching this lecturer
                matched_entries = []
                for e in entries:
                    for d in e.get("dosen_list", []):
                        if norm_lec in normalize_title(d) or normalize_title(d) in norm_lec:
                            matched_entries.append(e)
                            break

                if matched_entries:
                    first_dosen = matched_entries[0]["dosen_list"][0]
                    seen = set()
                    table_rows = []
                    
                    # Sort by day and time
                    matched_entries.sort(
                        key=lambda x: (
                            _DAY_ORDER.get(x.get("hari", ""), 99),
                            x.get("jam", ""),
                            x.get("mata_kuliah", ""),
                        )
                    )

                    for e in matched_entries:
                        key = (e.get("hari", ""), e.get("jam", ""), e.get("mata_kuliah", ""), e.get("kelas", ""))
                        if key in seen:
                            continue
                        seen.add(key)
                        table_rows.append(
                            f"| {e.get('hari', '-')} | "
                            f"{e.get('jam', '-')} | "
                            f"{e.get('mata_kuliah', '-')} | "
                            f"{e.get('kode_mk', '-')} | "
                            f"{e.get('prodi_full', e.get('prodi', '-'))} | "
                            f"{e.get('semester', '-')} | "
                            f"{e.get('ruang', '-')} |"
                        )

                    header = f"Jadwal mengajar resmi untuk **{first_dosen}**:"
                    table_header = [
                        "| Hari | Jam | Mata Kuliah | Kode MK | Program Studi | Semester | Ruang |",
                        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
                    ]
                    return f"{header}\n\n" + "\n".join(table_header + table_rows)

        # No positive match -> return None (NEVER return a refusal)
        return None


# Global singleton instance
_GLOBAL_ENTITY_INDEX: Optional[EntityIndex] = None


def get_entity_index(collection=None) -> EntityIndex:
    """Get or initialize the global EntityIndex singleton."""
    global _GLOBAL_ENTITY_INDEX
    if _GLOBAL_ENTITY_INDEX is None:
        _GLOBAL_ENTITY_INDEX = EntityIndex()
        if collection is not None:
            _GLOBAL_ENTITY_INDEX.build_from_collection(collection)
        else:
            from .store import get_chroma_collection
            _GLOBAL_ENTITY_INDEX.build_from_collection(get_chroma_collection())
    elif not _GLOBAL_ENTITY_INDEX._is_indexed and collection is not None:
        _GLOBAL_ENTITY_INDEX.build_from_collection(collection)
    return _GLOBAL_ENTITY_INDEX
