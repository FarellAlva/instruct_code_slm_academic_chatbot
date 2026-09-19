"""
app.py — Streamlit Chat Application for Pradita University AI Assistant.

Run with:
    streamlit run app.py
"""

import sys
import os
import re
import html
from typing import Optional, Tuple, List, Dict, Set, Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import time
import streamlit as st
from config import (
    BASE_DIR,
    DEFAULT_MODEL,
    DEFAULT_TEMPERATURE,
    DEFAULT_MAX_TOKENS,
    DEFAULT_TOP_K,
    TOP_K_RETRIEVAL,
    CHROMA_DIR,
    MAX_INPUT_CHARS,
    RATE_LIMIT_PER_MINUTE,
)
from rag.retriever       import retrieve_context
from rag.store           import get_chroma_collection
from rag.entity_index     import get_entity_index
from rag.scraper         import FACILITY_IMAGES
from rag.sanitize        import sanitize_user_input
from rag.output_guard    import guard_output
from llm.ollama_client   import stream_chat_with_context, check_ollama_connection


# ─── Facility Image Helper ────────────────────────────────────────────────────

FACILITY_KEYWORDS = [
    "fasilitas", "facility", "facilities", "gedung", "building", "kampus",
    "campus", "lab", "laboratorium", "perpustakaan", "library", "auditorium",
    "classroom", "ruang kelas", "kantin", "canteen", "asrama", "boarding",
    "shuttle", "kolam renang", "swimming", "gym", "sport", "olahraga",
    "vr room", "podcast", "workshop", "kitchen", "hotel", "lounge",
]

FOLLOW_UP_TOKENS = {
    "itu", "yang itu", "yang tadi", "semester berapa", "prodi apa", "jurusan apa",
    "ruang mana", "jam berapa", "hari apa", "kelas apa",
}

_FACILITY_ALIAS_MAP = {
    "lab": "laboratory",
    "laboratorium": "laboratory",
    "wine lab": "wine laboratory",
    "coffee lab": "coffee and tea laboratory",
    "tea lab": "coffee and tea laboratory",
    "mixology lab": "mixology laboratorium",
}


def _query_mentions_facilities(query: str) -> bool:
    q = query.lower()
    return any(kw in q for kw in FACILITY_KEYWORDS)


def _normalize_facility_query(query: str) -> str:
    normalized = query.lower()
    for raw, replacement in _FACILITY_ALIAS_MAP.items():
        normalized = normalized.replace(raw, replacement)
    normalized = re.sub(r"[^a-z0-9&]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def _get_matching_facility_images(query: str) -> list:
    q = _normalize_facility_query(query)
    image_dir = os.path.join(BASE_DIR, "data", "images")

    # Words that appear in almost every facility name but carry no intent
    img_stop_words = {"pradita", "university", "universitas", "kampus", "ada",
                      "apakah", "apa", "yang", "dari", "dan", "ini", "itu"}

    # Only search for facility images if the query explicitly mentions facilities
    if not _query_mentions_facilities(q):
        return []

    matching = []
    for img in FACILITY_IMAGES:
        name_lower = img["name"].lower()
        cat_lower  = img["category"].lower()
        score = 0
        for word in q.split():
            if len(word) > 2 and word not in img_stop_words and (word in name_lower or word in cat_lower):
                score += 1
        if score > 0:
            slug = re.sub(r'[^a-zA-Z0-9]+', '_', img['name']).strip('_').lower()
            ext  = img['url'].rsplit('.', 1)[-1].split('?')[0]
            filename = f"{slug}.{ext}"
            local_path = os.path.join(image_dir, filename)
            matching.append({
                "name": img["name"], "category": img["category"],
                "path": local_path, "url": img["url"], "score": score,
            })

    if not matching and _query_mentions_facilities(q):
        seen_cats = set()
        for img in FACILITY_IMAGES:
            if img["category"] not in seen_cats:
                seen_cats.add(img["category"])
                slug = re.sub(r'[^a-zA-Z0-9]+', '_', img['name']).strip('_').lower()
                ext  = img['url'].rsplit('.', 1)[-1].split('?')[0]
                filename = f"{slug}.{ext}"
                local_path = os.path.join(image_dir, filename)
                matching.append({
                    "name": img["name"], "category": img["category"],
                    "path": local_path, "url": img["url"], "score": 0,
                })

    matching.sort(key=lambda x: x["score"], reverse=True)
    return matching[:6]


def _build_facility_context(query: str) -> tuple[str, list[str]]:
    """
    Build deterministic facility facts from the curated facility catalog so the
    LLM can answer yes/no existence questions without guessing from loose text.
    """
    matches = _get_matching_facility_images(query)
    if not matches:
        return "", []

    context_lines = [
        "[Structured Facility Catalog]",
        "Gunakan katalog fasilitas berikut sebagai fakta eksplisit.",
    ]
    synthetic_sources = []

    for item in matches:
        synthetic_sources.append(f"facility:{item['name']}")
        context_lines.append(
            f"- Fasilitas tersedia: {item['name']} | kategori: {item['category']} | "
            f"path gambar lokal: {item['path']} | url gambar: {item['url']}"
        )

    context_lines.append(
        "Jika pengguna menanyakan apakah fasilitas tertentu ada, jawab 'ada' hanya jika nama fasilitas "
        "atau alias yang sangat mirip muncul pada katalog ini."
    )
    return "\n".join(context_lines), synthetic_sources


def _build_retrieval_query(current_prompt: str, messages: list) -> str:
    """
    Expand short follow-up questions with the last user turn so retrieval does
    not lose the active entity, e.g. "itu semester berapa".
    """
    prompt = current_prompt.strip()
    prompt_lower = prompt.lower()
    compact = re.sub(r"\s+", " ", prompt_lower)

    is_follow_up = any(token in compact for token in FOLLOW_UP_TOKENS)
    if not is_follow_up:
        return prompt

    previous_user_messages = [
        msg["content"].strip()
        for msg in reversed(messages[:-1])
        if msg["role"] == "user" and msg["content"].strip()
    ]
    if not previous_user_messages:
        return prompt

    last_user_query = previous_user_messages[0]
    return f"{last_user_query}\nFollow-up: {prompt}"


_LECTURER_QUERY_STOP_WORDS = {
    "siapa", "itu", "apa", "apakah", "ada", "di", "ke", "dari", "yang", "dan",
    "untuk", "jadwal", "berikan", "saya", "tolong", "bisa", "adalah", "ini",
    "beliau", "ngajar", "mengajar", "ampu", "mengampu", "mata", "kuliah",
    "semester", "prodi", "jurusan", "kelas", "ruang", "jam", "hari", "berapa",
    "bagaimana", "dengan", "tentang", "pak", "bu", "bapak", "ibu", "ajarkan",
    "ajar", "saja", "dosen", "genap", "ganjil", "periode", "tahun",
}
_DAY_ORDER = {
    "Senin": 0,
    "Selasa": 1,
    "Rabu": 2,
    "Kamis": 3,
    "Jumat": 4,
    "Sabtu": 5,
}
_ROMAN_TO_INT = {
    "I": 1,
    "II": 2,
    "III": 3,
    "IV": 4,
    "V": 5,
    "VI": 6,
    "VII": 7,
    "VIII": 8,
}


def _extract_lecturer_query_name(query: str) -> str:
    lowered = query.lower()
    if not any(token in lowered for token in ("dosen", "ajar", "ampu", "beliau", "ngajar", "mengajar")):
        return ""

    tokens = re.findall(r"[A-Za-z][A-Za-z'.-]*", query)
    filtered = [t for t in tokens if t.lower() not in _LECTURER_QUERY_STOP_WORDS]
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


def _normalize_lookup_text(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _clean_schedule_lecturer_name(raw_name: str) -> str:
    cleaned = re.sub(
        r"\b(?:AG\d{2}|[A-Z]\d{2,3}|F\d{2}|Smart Class|Multi Hall|Lab(?:\s+[A-Za-z0-9&.-]+)*)\b.*$",
        "",
        raw_name,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .,;")
    return cleaned


def _parse_schedule_chunk_entry(chunk_text: str) -> dict | None:
    if "Entri jadwal kuliah resmi." not in chunk_text:
        return None

    entry = {}
    for line in chunk_text.splitlines():
        clean = line.strip()
        if clean.startswith("Program studi:"):
            entry["program_studi"] = clean.split(":", 1)[1].strip().rstrip(".")
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
        elif clean.startswith("Kelas:"):
            entry["kelas"] = clean.split(":", 1)[1].strip().rstrip(".")
        elif clean.startswith("Ruang:"):
            entry["ruang"] = clean.split(":", 1)[1].strip().rstrip(".")
        elif clean.startswith("Dosen pengampu tertulis:"):
            raw = clean.split(":", 1)[1].strip().rstrip(".")
            entry["lecturers"] = [
                cleaned_name
                for cleaned_name in (_clean_schedule_lecturer_name(name) for name in raw.split(";"))
                if cleaned_name and len(cleaned_name.split()) >= 2
            ]

    return entry if entry.get("mata_kuliah") and entry.get("lecturers") else None


def _extract_requested_semesters(query: str) -> set[str]:
    requested = set()
    lowered = query.lower()

    for match in re.findall(r"\bsemester\s+([ivx]+|\d+)\b", lowered):
        token = match.upper()
        if token.isdigit():
            int_to_roman = {value: key for key, value in _ROMAN_TO_INT.items()}
            roman = int_to_roman.get(int(token))
            if roman:
                requested.add(roman)
        else:
            requested.add(token)

    return requested


import difflib

PRODI_ALIAS_MAP = {
    "teknik informatika": "INF", "informatika": "INF", "infromatika": "INF", "infomatika": "INF",
    "it": "INF", "ti": "INF", "inf": "INF", "komputer": "INF",
    "teknik sipil": "TS", "sipil": "TS", "ts": "TS",
    "sistem informasi": "SI", "sisfo": "SI", "si": "SI",
    "desain komunikasi visual": "DKV", "dkv": "DKV",
    "desain interior": "DI", "interior": "DI", "di": "DI",
    "arsitektur": "AR", "arsitek": "AR", "ars": "AR", "ar": "AR",
    "seni kuliner": "SK", "kuliner": "SK", "sk": "SK",
    "akuntansi": "AK", "accounting": "AK", "ak": "AK",
    "manajemen bisnis": "MB", "manajemen": "MB", "retail": "MR", "mb": "MB", "mr": "MR",
    "pariwisata": "PAR", "hospitality": "PAR", "hotel": "PAR", "par": "PAR", "f&b": "F&B",
    "perencanaan wilayah dan kota": "PWK", "pwk": "PWK", "planologi": "PWK",
    "mkdu": "MKDU",
}

FUZZY_PRODI_TARGETS = {
    "informatika": "INF",
    "sipil": "TS",
    "arsitektur": "AR",
    "akuntansi": "AK",
    "pariwisata": "PAR",
    "kuliner": "SK",
    "interior": "DI",
    "planologi": "PWK",
}


def _extract_slots(
    query: str,
    current_prodi: Optional[str] = None,
    current_sem: Optional[str] = None,
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Extract prodi, semester, and day slots from query and previous session state."""
    q_lower = query.lower()

    # 1. Prodi detection with alias resolution and typo tolerance
    detected_prodi = None
    for alias in sorted(PRODI_ALIAS_MAP.keys(), key=len, reverse=True):
        if re.search(r"\b" + re.escape(alias) + r"\b", q_lower):
            detected_prodi = PRODI_ALIAS_MAP[alias]
            break

    if not detected_prodi:
        words = re.findall(r"[a-z]+", q_lower)
        for w in words:
            if len(w) >= 5:
                matches = difflib.get_close_matches(w, list(FUZZY_PRODI_TARGETS.keys()), n=1, cutoff=0.72)
                if matches:
                    detected_prodi = FUZZY_PRODI_TARGETS[matches[0]]
                    break

    prodi = detected_prodi or current_prodi

    # 2. Semester detection
    detected_sem = None
    sem_match = re.search(r"\bsemester\s+([ivx]+|\d+)\b", q_lower) or re.search(r"\bsmt\s+([ivx]+|\d+)\b", q_lower)
    if sem_match:
        val = sem_match.group(1).upper()
        if val.isdigit():
            val = {1: "I", 2: "II", 3: "III", 4: "IV", 5: "V", 6: "VI", 7: "VII", 8: "VIII"}.get(int(val), val)
        detected_sem = val
    semester = detected_sem or current_sem

    # 3. Hari detection
    hari = None
    for d in ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu"]:
        if d.lower() in q_lower:
            hari = d
            break

    return prodi, semester, hari


def _build_direct_schedule_answer(query: str, collection=None) -> str:
    """
    Query the entity index / ScheduleSource for deterministic positive-only answers:
    - course instructor lookup
    - lecturer schedule lookup
    - prodi + semester + hari schedule lookup with slot tracking
    - single clarifying question when query is ambiguous
    """
    # 1. Check EntityIndex for direct course or lecturer match
    entity_idx = get_entity_index(collection)
    ans = entity_idx.answer_direct_query(query)
    if ans:
        return ans

    # 2. Check for Schedule lookup with slot memory
    from rag.schedule_source import get_schedule_source
    sched_src = get_schedule_source()

    slot_p = st.session_state.get("slot_prodi")
    slot_s = st.session_state.get("slot_semester")

    prodi, semester, hari = _extract_slots(query, current_prodi=slot_p, current_sem=slot_s)

    # Update session slots if found in query
    if prodi:
        st.session_state.slot_prodi = prodi
    if semester:
        st.session_state.slot_semester = semester

    q_lower = query.lower()
    is_asking_schedule = any(k in q_lower for k in ["jadwal", "matkul apa", "kuliah apa", "kelas apa"]) or (hari and (slot_p or slot_s))

    # Disambiguation 1: "teknik" alone without specifying prodi
    if re.search(r"\bteknik\b", q_lower) and not re.search(r"\b(?:sipil|informatika|infromatika|inf|ti|ts)\b", q_lower):
        return (
            "Di Pradita University terdapat program studi **Teknik Sipil** dan **Informatika (Teknik Informatika)**. "
            "Boleh konfirmasi program studi mana yang kamu maksud, sobat?"
        )

    # Disambiguation 2: Asking for schedule or lecturers without mentioning prodi or specific entity
    if not prodi and not entity_idx.match_course(query) and not entity_idx.match_lecturer(query):
        if any(k in q_lower for k in ["jadwal", "matkul apa", "kuliah apa", "kelas apa"]) and len(query.split()) <= 7:
            return "Tentu sobat, untuk melihat jadwal perkuliahan, boleh sebutkan program studi (prodi) apa yang kamu maksud?"
        if any(k in q_lower for k in ["siapa saja dosen", "daftar dosen", "dosen pengampu", "siapa dosen"]) and len(query.split()) <= 7:
            return (
                "Tentu sobat, untuk memberikan daftar dosen yang tepat, boleh sebutkan program studi (jurusan) yang kamu maksud? "
                "(Contoh: Informatika, Sistem Informasi, Teknik Sipil, Desain Komunikasi Visual, dll.)"
            )

    if is_asking_schedule:
        # Check if we have prodi + semester (and optionally hari)
        if prodi and semester:
            records = sched_src.search(prodi=prodi, semester=semester, hari=hari)
            if records:
                prodi_name = records[0].get("prodi_full", prodi)
                hari_info = f" untuk hari **{hari}**" if hari else ""
                table = sched_src.format_markdown_table(records)
                header = f"Berikut jadwal perkuliahan **{prodi_name}** Semester **{semester}**{hari_info}:"
                return f"{header}\n\n{table}"

    # 3. Check for Prodi Lecturers list (e.g. "siapa saja dosen informatika", "daftar dosen sistem informasi")
    is_asking_prodi_lecturers = (
        any(w in q_lower for w in ["dosen", "pengajar", "guru"])
        and prodi
        and not entity_idx.match_lecturer(query)
        and not entity_idx.match_course(query)
    )
    if is_asking_prodi_lecturers:
        records = sched_src.search(prodi=prodi)
        if records:
            from rag.entity_index import normalize_title
            prodi_name = records[0].get("prodi_full", prodi)
            canonical_names: Dict[str, str] = {}
            lec_to_courses: Dict[str, Set[str]] = {}

            for r in records:
                mk = r.get("mata_kuliah", "").strip(" ,.-")
                if not mk:
                    continue
                for d in r.get("dosen", []):
                    d_clean = d.strip(" ,.-")
                    if not d_clean or d_clean == "-":
                        continue
                    key = normalize_title(d_clean)
                    if not key or len(key.split()) < 1:
                        key = d_clean.lower()
                    if key not in canonical_names or len(d_clean) > len(canonical_names[key]):
                        canonical_names[key] = d_clean
                    lec_to_courses.setdefault(key, set()).add(mk)

            if lec_to_courses:
                people = {}
                labs = {}
                placeholders = {}

                for key, courses in lec_to_courses.items():
                    lec_name = canonical_names[key]
                    n_lower = lec_name.lower()
                    if re.match(r"^[XYZ]\s*\(.*?\)$", lec_name, re.IGNORECASE) or n_lower in ("tba", "tbd", "belum ada"):
                        placeholders[lec_name] = courses
                    elif any(k in n_lower for k in ["laboratorium", "aslab", "asisten lab"]):
                        labs[lec_name] = courses
                    else:
                        people[lec_name] = courses

                sections = [f"Berikut daftar dosen pengampu di Program Studi **{prodi_name}** beserta mata kuliah yang diajarkan:"]

                # 1. Dosen Pengampu Akademik
                if people:
                    sections.append("\n### 👨‍🏫 Dosen Pengampu")
                    p_rows = [
                        f"| **{p}** | {', '.join(sorted(people[p]))} |"
                        for p in sorted(people.keys())
                    ]
                    sections.append("| Dosen Pengampu | Mata Kuliah yang Diampu |\n| :--- | :--- |\n" + "\n".join(p_rows))

                # 2. Praktikum & Laboratorium
                if labs:
                    sections.append("\n### 🔬 Praktikum & Laboratorium")
                    l_rows = [
                        f"| **{l}** | {', '.join(sorted(labs[l]))} |"
                        for l in sorted(labs.keys())
                    ]
                    sections.append("| Pengampu / Fasilitas Lab | Mata Kuliah Praktikum |\n| :--- | :--- |\n" + "\n".join(l_rows))

                # 3. Placeholder / Belum Ditentukan
                if placeholders:
                    sections.append("\n### ⏳ Belum Ditentukan (TBA / Placeholder)")
                    pl_rows = [
                        f"| `{pl}` | {', '.join(sorted(placeholders[pl]))} |"
                        for pl in sorted(placeholders.keys())
                    ]
                    sections.append("| Kode Jadwal | Mata Kuliah |\n| :--- | :--- |\n" + "\n".join(pl_rows))
                    sections.append("\n*Catatan: Entri bertanda kode huruf seperti `Y (Teknik Lalu Lintas)` adalah placeholder resmi dari fakultas untuk mata kuliah yang dosen pengampunya belum ditetapkan saat jadwal perkuliahan diterbitkan.*")

                return "\n\n".join(sections)

    return ""


# ─── Page Config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title  = "Pradita University AI Assistant",
    layout      = "wide",
    initial_sidebar_state = "expanded",
)

# ─── Custom CSS — Pradita University Branding ─────────────────────────────────
# Primary: #C1272D (Pradita Red/Maroon)
# Secondary: #1A1A2E (Dark Navy)
# Accent: #F5F5F5 (Light Gray), #FFFFFF (White)
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* ── Header Banner ── */
    .pradita-header {
        background: linear-gradient(135deg, #C1272D 0%, #8B1A1F 60%, #1A1A2E 100%);
        padding: 28px 36px;
        border-radius: 12px;
        margin-bottom: 24px;
        display: flex;
        align-items: center;
        gap: 20px;
        box-shadow: 0 4px 20px rgba(193, 39, 45, 0.25);
    }
    .pradita-header-text {
        flex: 1;
    }
    .pradita-header-text h1 {
        font-size: 26px;
        font-weight: 700;
        color: #FFFFFF;
        margin: 0;
        letter-spacing: -0.3px;
    }
    .pradita-header-text p {
        font-size: 13px;
        color: rgba(255, 255, 255, 0.75);
        margin: 4px 0 0 0;
    }
    .pradita-badge {
        display: inline-block;
        background: rgba(255,255,255,0.15);
        backdrop-filter: blur(8px);
        color: white;
        font-size: 11px;
        font-weight: 600;
        padding: 4px 14px;
        border-radius: 20px;
        margin-top: 10px;
        letter-spacing: 0.8px;
        text-transform: uppercase;
        border: 1px solid rgba(255,255,255,0.25);
    }

    /* ── Sidebar ── */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1A1A2E 0%, #16213E 100%);
    }
    [data-testid="stSidebar"] .stMarkdown h2 {
        color: #E8A0A4;
        font-size: 12px;
        font-weight: 600;
        letter-spacing: 1.5px;
        text-transform: uppercase;
    }
    [data-testid="stSidebar"] label {
        color: #D0D0D0 !important;
    }

    /* ── Chat Messages ── */
    .stChatMessage {
        border-radius: 12px;
        padding: 14px 18px;
    }

    /* ── Source Chips ── */
    .source-chip {
        display: inline-block;
        background: rgba(193, 39, 45, 0.08);
        color: #C1272D;
        border: 1px solid rgba(193, 39, 45, 0.2);
        border-radius: 6px;
        padding: 3px 10px;
        font-size: 11px;
        font-weight: 500;
        margin: 2px 3px;
    }

    /* ── Status Pills ── */
    .status-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 5px 14px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
    }
    .status-ok {
        background: rgba(46,160,67,0.15);
        color: #2EA043;
        border: 1px solid rgba(46,160,67,0.3);
    }
    .status-fail {
        background: rgba(248,81,73,0.15);
        color: #D73A49;
        border: 1px solid rgba(248,81,73,0.3);
    }

    /* ── Knowledge Base Badge ── */
    .kb-badge {
        background: rgba(193, 39, 45, 0.1);
        color: #C1272D;
        padding: 6px 14px;
        border-radius: 8px;
        font-size: 13px;
        font-weight: 600;
        text-align: center;
        border: 1px solid rgba(193, 39, 45, 0.15);
    }

    /* ── Facility image grid ── */
    .facility-section-title {
        font-size: 14px;
        font-weight: 600;
        color: #555;
        margin-top: 12px;
        margin-bottom: 8px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Barlow:wght@500;600;700;800&family=Source+Sans+3:wght@400;500;600;700&display=swap');

    :root {
        --summarecon-orange: #c9792b;
        --summarecon-gold: #d9a441;
        --pradita-green: #4c6b5f;
        --text-strong: #4b433d;
        --text-muted: #766f68;
        --line: #d8cec2;
        --surface-base: #f4efe8;
        --surface-panel: #f8f4ee;
        --surface-card: #fcfaf7;
        --topbar-bg: rgba(252, 249, 244, 0.92);
        --topbar-line: rgba(201, 121, 43, 0.10);
        --bottombar-bg: rgba(244, 239, 232, 0.96);
        --success: #009a2b;
        --danger: #d71920;
        --shadow-soft: 0 18px 42px rgba(75, 67, 61, 0.08);
    }

    html, body, [class*="css"] {
        font-family: 'Source Sans 3', sans-serif;
        color: var(--text-strong);
    }
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Barlow', sans-serif !important;
        letter-spacing: 0.01em;
    }
    .stApp {
        background:
            radial-gradient(circle at top left, rgba(217,164,65,0.08), transparent 22%),
            linear-gradient(180deg, #f7f2eb 0%, #efe7de 100%);
    }
    [data-testid="stAppViewContainer"] {
        background:
            radial-gradient(circle at top left, rgba(217,164,65,0.08), transparent 22%),
            linear-gradient(180deg, #f7f2eb 0%, #efe7de 100%);
    }
    [data-testid="stHeader"] {
        background: var(--topbar-bg) !important;
        border-bottom: 1px solid var(--topbar-line);
        backdrop-filter: blur(10px);
    }
    [data-testid="stToolbar"] {
        right: 1rem;
        color: var(--text-muted) !important;
    }
    [data-testid="stToolbar"] * {
        color: var(--text-muted) !important;
    }
    [data-testid="stDecoration"] {
        background: linear-gradient(90deg, rgba(201,121,43,0.55), rgba(217,164,65,0.35), rgba(76,107,95,0.35)) !important;
        height: 3px !important;
    }
    footer,
    .stApp > footer,
    [data-testid="stBottomBlockContainer"] {
        background: var(--bottombar-bg) !important;
    }
    .block-container {
        padding-top: 1.75rem;
        padding-bottom: 7rem;
        max-width: 1120px;
        margin: 0 auto;
    }
    .pradita-header {
        display: none;
    }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #f8f4ee 0%, #f0e8df 100%) !important;
        border-right: 1px solid var(--line);
        box-shadow: inset -1px 0 0 rgba(255,255,255,0.45);
    }
    [data-testid="stSidebar"] .stMarkdown h2 {
        color: var(--pradita-green);
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0.14em;
        text-transform: uppercase;
    }
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] .stCaption {
        color: var(--text-strong) !important;
    }
    .summarecon-hero {
        position: relative;
        overflow: hidden;
        border-radius: 28px;
        margin-bottom: 1.4rem;
        background:
            linear-gradient(118deg, rgba(252,250,247,0.98) 0%, rgba(248,244,238,0.95) 54%, rgba(201,121,43,0.10) 100%);
        border: 1px solid rgba(201,121,43,0.14);
        box-shadow: var(--shadow-soft);
    }
    .summarecon-hero::before {
        content: "";
        position: absolute;
        inset: 0;
        background:
            linear-gradient(90deg, transparent 0 76%, rgba(76,107,95,0.06) 76% 100%),
            linear-gradient(180deg, transparent 0 84%, rgba(217,164,65,0.08) 84% 100%);
        pointer-events: none;
    }
    .summarecon-hero-inner {
        position: relative;
        z-index: 1;
        display: grid;
        grid-template-columns: minmax(0, 1.45fr) minmax(280px, 0.75fr);
        gap: 1.4rem;
        padding: 2rem 2.1rem;
        align-items: end;
    }
    .brand-lockup {
        display: flex;
        gap: 1rem;
        align-items: flex-start;
    }
    .brand-mark {
        display: flex;
        gap: 0.28rem;
        padding-top: 0.1rem;
    }
    .brand-mark span {
        display: block;
        width: 8px;
        border-radius: 999px;
    }
    .brand-mark span:nth-child(1) { height: 44px; background: var(--summarecon-gold); }
    .brand-mark span:nth-child(2) { height: 54px; background: var(--summarecon-orange); }
    .brand-mark span:nth-child(3) { height: 36px; background: var(--pradita-green); }
    .brand-copy small {
        display: inline-block;
        margin-bottom: 0.55rem;
        color: var(--summarecon-orange);
        font-family: 'Barlow', sans-serif;
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0.16em;
        text-transform: uppercase;
    }
    .brand-copy h1 {
        margin: 0;
        color: var(--pradita-green);
        font-size: clamp(2.1rem, 3vw, 3rem);
        font-weight: 800;
        line-height: 0.95;
        text-transform: uppercase;
    }
    .brand-copy p {
        margin: 0.85rem 0 0;
        max-width: 42rem;
        color: var(--text-muted);
        font-size: 1.05rem;
        line-height: 1.5;
    }
    .hero-panel {
        background: rgba(252,250,247,0.88);
        border: 1px solid rgba(76,107,95,0.12);
        border-radius: 22px;
        padding: 1.1rem 1.2rem;
        backdrop-filter: blur(10px);
        box-shadow: 0 10px 24px rgba(75,67,61,0.05);
    }
    .hero-panel-title {
        color: var(--text-muted);
        font-family: 'Barlow', sans-serif;
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0.14em;
        text-transform: uppercase;
        margin-bottom: 0.7rem;
    }
    .hero-panel-value {
        color: var(--text-strong);
        font-family: 'Barlow', sans-serif;
        font-size: 1.9rem;
        font-weight: 700;
        line-height: 1;
        margin-bottom: 0.35rem;
    }
    .hero-panel-caption {
        color: var(--text-muted);
        font-size: 0.98rem;
        line-height: 1.45;
    }
    .accent-rail {
        display: flex;
        gap: 0.45rem;
        margin-top: 1.2rem;
    }
    .accent-rail span {
        height: 6px;
        border-radius: 999px;
    }
    .accent-rail span:nth-child(1) { width: 56px; background: var(--pradita-green); }
    .accent-rail span:nth-child(2) { width: 38px; background: var(--summarecon-gold); }
    .accent-rail span:nth-child(3) { width: 74px; background: var(--summarecon-orange); }
    .stChatMessage {
        border-radius: 22px;
        padding: 1rem 1.15rem;
        border: 1px solid rgba(216,206,194,0.9);
        box-shadow: 0 10px 26px rgba(75,67,61,0.04);
        background: rgba(252,250,247,0.96);
    }
    [data-testid="stChatMessageContainer"] {
        background: transparent !important;
        margin-bottom: 0.75rem;
    }
    [data-testid="stChatMessageContent"] p {
        color: var(--text-strong);
        font-size: 1rem;
        line-height: 1.62;
    }
    [data-testid="stMarkdownContainer"] p,
    [data-testid="stMarkdownContainer"] li,
    [data-testid="stMarkdownContainer"] span,
    [data-testid="stMarkdownContainer"] label {
        color: var(--text-strong);
    }
    [data-testid="stMarkdownContainer"] strong {
        color: #3f3833;
    }
    [data-testid="stMarkdownContainer"] a {
        color: var(--pradita-green);
    }
    [data-testid="stChatMessageContent"] [data-testid="stMarkdownContainer"] {
        overflow-x: auto;
    }
    [data-testid="stMarkdownContainer"] table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 0;
        margin: 0.85rem 0 1rem 0;
        overflow: hidden;
        border: 1px solid rgba(216,206,194,0.92);
        border-radius: 14px;
        background: rgba(255,255,255,0.96);
        color: var(--text-strong) !important;
        box-shadow: 0 6px 18px rgba(75,67,61,0.04);
    }
    [data-testid="stMarkdownContainer"] thead tr {
        background: linear-gradient(180deg, rgba(255,249,240,0.98), rgba(247,239,230,0.96));
    }
    [data-testid="stMarkdownContainer"] tbody tr:nth-child(even) {
        background: rgba(255,251,247,0.92);
    }
    [data-testid="stMarkdownContainer"] tbody tr:nth-child(odd) {
        background: rgba(255,255,255,0.96);
    }
    [data-testid="stMarkdownContainer"] th,
    [data-testid="stMarkdownContainer"] td {
        padding: 0.78rem 0.85rem;
        text-align: left;
        vertical-align: top;
        border-bottom: 1px solid rgba(232,223,213,0.92);
        color: var(--text-strong) !important;
        background: transparent !important;
    }
    [data-testid="stMarkdownContainer"] th {
        font-family: 'Barlow', sans-serif;
        font-size: 0.84rem;
        font-weight: 700;
        letter-spacing: 0.03em;
        color: #4a443f !important;
    }
    [data-testid="stMarkdownContainer"] tr:last-child td {
        border-bottom: none;
    }
    [data-testid="stMarkdownContainer"] table code,
    [data-testid="stMarkdownContainer"] td code,
    [data-testid="stMarkdownContainer"] th code,
    [data-testid="stMarkdownContainer"] p code,
    [data-testid="stMarkdownContainer"] li code {
        display: inline;
        padding: 0.08rem 0.32rem;
        border-radius: 6px;
        background: rgba(220,138,54,0.10) !important;
        color: var(--text-strong) !important;
        border: 1px solid rgba(220,138,54,0.10);
        box-shadow: none !important;
        white-space: normal;
    }
    [data-testid="stCodeBlock"] pre,
    code {
        color: #5a514b !important;
    }
    .source-chip {
        display: inline-block;
        background: rgba(76,107,95,0.08);
        color: var(--pradita-green);
        border: 1px solid rgba(76,107,95,0.12);
        border-radius: 999px;
        padding: 0.24rem 0.72rem;
        font-size: 0.77rem;
        font-weight: 600;
        margin: 0.18rem 0.2rem 0 0;
    }
    .status-pill {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        padding: 0.42rem 0.88rem;
        border-radius: 999px;
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0.05em;
        text-transform: uppercase;
    }
    .status-ok {
        background: rgba(0,154,43,0.12);
        color: var(--success);
        border: 1px solid rgba(0,154,43,0.2);
    }
    .status-fail {
        background: rgba(215,25,32,0.11);
        color: var(--danger);
        border: 1px solid rgba(215,25,32,0.18);
    }
    .kb-badge {
        background: linear-gradient(90deg, rgba(201,121,43,0.11), rgba(217,164,65,0.11));
        color: var(--text-strong);
        padding: 0.68rem 0.95rem;
        border-radius: 16px;
        font-size: 0.96rem;
        font-weight: 700;
        text-align: center;
        border: 1px solid rgba(201,121,43,0.14);
    }
    .facility-section-title {
        color: var(--pradita-green);
        font-family: 'Barlow', sans-serif;
        font-size: 0.9rem;
        font-weight: 700;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        margin-top: 0.75rem;
        margin-bottom: 0.55rem;
    }
    .stChatInput > div {
        border-radius: 18px;
        border: 1px solid rgba(201,121,43,0.14);
        background: rgba(252,250,247,0.98);
        box-shadow: 0 12px 26px rgba(75,67,61,0.04);
    }
    section[data-testid="stChatInput"] {
        background: linear-gradient(180deg, rgba(244,239,232,0.72), rgba(244,239,232,0.94));
        border-top: 1px solid rgba(201,121,43,0.08);
        padding-top: 0.75rem;
        padding-bottom: 0.75rem;
        position: sticky;
        bottom: 0;
        z-index: 20;
        backdrop-filter: blur(12px);
    }
    .stChatInput textarea {
        color: var(--text-strong) !important;
    }
    .stSlider [data-baseweb="slider"] > div > div {
        background: rgba(201,121,43,0.20) !important;
    }
    .stSlider [role="slider"] {
        background: var(--summarecon-orange) !important;
        border: 2px solid #fff7ef !important;
        box-shadow: 0 0 0 1px rgba(201,121,43,0.15);
    }
    .stTextInput input,
    .stNumberInput input,
    .stTextArea textarea {
        background: var(--surface-card) !important;
        color: var(--text-strong) !important;
        border: 1px solid rgba(216,206,194,0.95) !important;
    }
    [data-testid="stExpander"] {
        background: rgba(252,250,247,0.78);
        border: 1px solid rgba(216,206,194,0.9);
        border-radius: 18px;
        overflow: hidden;
    }
    [data-testid="stExpander"] summary {
        padding: 0.95rem 1.1rem;
        background: rgba(255,255,255,0.72);
    }
    [data-testid="stExpander"] summary *,
    [data-testid="stExpander"] summary p,
    [data-testid="stExpander"] summary span,
    [data-testid="stExpander"] summary svg {
        color: var(--summarecon-orange) !important;
        fill: var(--summarecon-orange) !important;
    }
    [data-testid="stExpanderDetails"] {
        padding: 0.4rem 1rem 1rem 1rem;
    }
    [data-testid="stExpanderDetails"] [data-testid="stMarkdownContainer"] p,
    [data-testid="stExpanderDetails"] [data-testid="stMarkdownContainer"] li,
    [data-testid="stExpanderDetails"] [data-testid="stMarkdownContainer"] span,
    [data-testid="stExpanderDetails"] [data-testid="stMarkdownContainer"] strong {
        color: var(--summarecon-orange) !important;
    }
    [data-testid="stExpanderDetails"] [data-testid="stMarkdownContainer"] code {
        color: var(--summarecon-orange) !important;
        background: rgba(220,138,54,0.08) !important;
        border: 1px solid rgba(220,138,54,0.12) !important;
    }
    [data-testid="stExpanderDetails"] [data-testid="stMarkdownContainer"] pre {
        color: #3f362f !important;
        -webkit-text-fill-color: #3f362f !important;
    }
    .debug-chunk-card {
        background: rgba(255,255,255,0.92);
        border: 1px solid rgba(216,206,194,0.92);
        border-radius: 18px;
        padding: 0.95rem 1rem;
        margin: 0.75rem 0;
        box-shadow: 0 8px 22px rgba(75,67,61,0.04);
    }
    .debug-chunk-meta {
        display: flex;
        flex-wrap: wrap;
        gap: 0.45rem;
        align-items: center;
        margin-bottom: 0.75rem;
    }
    .debug-chunk-title {
        color: var(--summarecon-orange);
        font-family: 'Barlow', sans-serif;
        font-size: 0.96rem;
        font-weight: 700;
        margin-right: 0.25rem;
    }
    .debug-chip {
        display: inline-flex;
        align-items: center;
        border-radius: 999px;
        padding: 0.2rem 0.65rem;
        background: rgba(220,138,54,0.08);
        border: 1px solid rgba(220,138,54,0.10);
        color: var(--summarecon-orange);
        font-size: 0.8rem;
        line-height: 1.2;
    }
    .debug-chunk-pre {
        margin: 0;
        max-height: 230px;
        overflow: auto;
        padding: 0.9rem 1rem;
        border-radius: 14px;
        background: #f7f2ec;
        border: 1px solid rgba(216,206,194,0.9);
        color: #544c46;
        font-family: Consolas, 'Courier New', monospace;
        font-size: 0.84rem;
        line-height: 1.55;
        white-space: pre-wrap;
        word-break: break-word;
    }
    .debug-chunk-pre,
    .debug-chunk-pre *,
    .debug-chunk-pre code {
        color: #3f362f !important;
        -webkit-text-fill-color: #3f362f !important;
    }
    [data-testid="stExpanderDetails"] .debug-chunk-pre,
    [data-testid="stExpanderDetails"] .debug-chunk-pre * {
        color: #3f362f !important;
        -webkit-text-fill-color: #3f362f !important;
        opacity: 1 !important;
    }
    .debug-chunk-pre::selection,
    .debug-chunk-pre *::selection {
        background: rgba(220,138,54,0.30);
        color: #241a14 !important;
        -webkit-text-fill-color: #241a14 !important;
    }
    .debug-panel-note {
        color: var(--summarecon-orange);
        font-size: 0.9rem;
        margin: 0.1rem 0 0.35rem 0;
    }
    .stButton > button {
        background: linear-gradient(135deg, var(--summarecon-orange), #b96b24);
        color: white;
        border: none;
        border-radius: 12px;
        font-family: 'Barlow', sans-serif;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, #ba6d25, #a85f1f);
        color: white;
        border: none;
    }
    .stAlert,
    [data-baseweb="notification"] {
        background: rgba(252,250,247,0.96) !important;
        color: var(--text-strong) !important;
        border: 1px solid rgba(216,206,194,0.9) !important;
    }
    .stAlert * ,
    [data-baseweb="notification"] * {
        color: var(--text-strong) !important;
    }
    @media (max-width: 900px) {
        .summarecon-hero-inner {
            grid-template-columns: 1fr;
        }
        .block-container {
            padding-left: 1rem;
            padding-right: 1rem;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ─── Session State ─────────────────────────────────────────────────────────────
if "messages"   not in st.session_state:
    st.session_state.messages   = []
if "collection" not in st.session_state:
    st.session_state.collection = None
if "ollama_ok"  not in st.session_state:
    st.session_state.ollama_ok  = None


@st.cache_resource(show_spinner="Memuat knowledge base…")
def load_collection():
    return get_chroma_collection(CHROMA_DIR)


# ─── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## Model Settings")

    model_name = st.text_input("Model", value=DEFAULT_MODEL)

    temperature = st.slider(
        "Temperature", 0.0, 2.0, DEFAULT_TEMPERATURE, 0.05,
        help="Semakin tinggi = semakin kreatif; semakin rendah = semakin fokus"
    )
    max_tokens = st.slider(
        "Max Tokens", 64, 2048, DEFAULT_MAX_TOKENS, 64,
        help="Maksimal token dalam respons"
    )
    top_k = st.slider(
        "Top-K Retrieval", 1, 10, TOP_K_RETRIEVAL, 1,
        help="Jumlah dokumen yang ditarik per query"
    )

    st.divider()

    debug_mode = st.toggle("Debug Mode", value=False,
                            help="Tampilkan chunk yang ditarik dan skor reranker")

    st.divider()
    st.markdown("## System Status")

    col_check, col_clear = st.columns(2)
    with col_check:
        if st.button("Check Ollama", use_container_width=True):
            result = check_ollama_connection(model_name)
            st.session_state.ollama_ok = result["ok"]
            st.info(result["message"])

    with col_clear:
        if st.button("Clear Chat", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

    if st.session_state.ollama_ok is True:
        st.markdown(
            '<span class="status-pill status-ok">Connected</span>',
            unsafe_allow_html=True,
        )
    elif st.session_state.ollama_ok is False:
        st.markdown(
            '<span class="status-pill status-fail">Offline</span>',
            unsafe_allow_html=True,
        )

    st.divider()
    st.markdown("## Knowledge Base")

    collection = load_collection()
    st.session_state.collection = collection
    doc_count  = collection.count()

    if doc_count == 0:
        st.warning(
            "Knowledge base kosong.\n\n"
            "Jalankan `python ingest.py` untuk memuat data."
        )
    else:
        st.markdown(
            f'<div class="kb-badge">{doc_count} chunks loaded</div>',
            unsafe_allow_html=True,
        )

    st.divider()
    st.markdown("## Context Memory")
    
    # Calculate token estimate from last 6 messages
    recent_msgs = st.session_state.messages[-6:] if "messages" in st.session_state else []
    history_str = " ".join(m.get("content", "") for m in recent_msgs)
    est_tokens = int(len(history_str.split()) * 1.3) + 150 # Base prompt overhead
    max_ctx = 2048
    
    percent = min(est_tokens / max_ctx, 1.0)
    st.progress(percent)
    st.caption(f"**{est_tokens}** / {max_ctx} Tokens ({int(percent * 100)}%)")

    st.divider()
    st.caption("Pradita University AI Chatbot v2.0")


# ─── Header ───────────────────────────────────────────────────────────────────
st.markdown(
    """<div class="summarecon-hero">
<div class="summarecon-hero-inner">
<div>
<div class="brand-lockup">
<div class="brand-mark">
<span></span>
<span></span>
<span></span>
</div>
<div class="brand-copy">
<small>Academic Knowledge Workspace</small>
<h1>Pradita University AI Assistant</h1>
<p>Pradita University.</p>
</div>
</div>
<div class="accent-rail">
<span></span>
<span></span>
<span></span>
</div>
</div>
<div class="hero-panel">
<div class="hero-panel-title">Knowledge Layer</div>
<div class="hero-panel-value">Pradita Chatbot</div>
<div class="hero-panel-caption">
Chat akademik berdasarkan jadwal dan fasilitas yang tersedia.
</div>
</div>
</div>
</div>""",
    unsafe_allow_html=True,
)

# ─── Chat History Display ──────────────────────────────────────────────────────
for msg in st.session_state.messages:
    avatar = ":material/support_agent:" if msg["role"] == "assistant" else ":material/person:"
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["content"])

        if msg["role"] == "assistant" and msg.get("sources"):
            source_html = " ".join(
                f'<span class="source-chip">{html.escape(str(s))}</span>' for s in msg["sources"]
            )
            st.markdown(f"<div style='margin-top:8px'>{source_html}</div>",
                        unsafe_allow_html=True)

# ─── Chat Input ───────────────────────────────────────────────────────────────
if prompt := st.chat_input("Tanyakan seputar Pradita University…"):

    # Session Rate Limiting (Fase 2.3)
    if "request_timestamps" not in st.session_state:
        st.session_state.request_timestamps = []

    now = time.time()
    st.session_state.request_timestamps = [
        t for t in st.session_state.request_timestamps if now - t < 60.0
    ]
    if len(st.session_state.request_timestamps) >= RATE_LIMIT_PER_MINUTE:
        st.warning(
            f"⚠️ Batas permintaan tercapai (maksimal {RATE_LIMIT_PER_MINUTE} pertanyaan per menit). "
            "Mohon tunggu sebentar sebelum mengirim pertanyaan lagi."
        )
        st.stop()
    st.session_state.request_timestamps.append(now)

    # Input length bounding and sanitization (Fase 2.2 & 2.3)
    raw_prompt = prompt
    if len(raw_prompt) > MAX_INPUT_CHARS:
        st.info(f"ℹ️ Pertanyaan dipotong menjadi maksimal {MAX_INPUT_CHARS} karakter.")

    clean_prompt, is_suspicious, reasons = sanitize_user_input(raw_prompt, max_chars=MAX_INPUT_CHARS)
    if is_suspicious:
        print(f"[SECURITY] Input matched suspicious prompt injection patterns: {reasons}")

    prompt = clean_prompt

    with st.chat_message("user", avatar=":material/person:"):
        st.markdown(prompt)

    st.session_state.messages.append({"role": "user", "content": prompt})

    # Retrieve context from RAG
    retrieval_query = _build_retrieval_query(prompt, st.session_state.messages)

    rag_result = retrieve_context(
        query      = retrieval_query,
        top_k      = top_k,
        collection = st.session_state.collection,
    )

    facility_context, facility_sources = _build_facility_context(prompt)
    if facility_context:
        rag_result["context"] = (
            facility_context
            if not rag_result["context"]
            else facility_context + "\n\n---\n\n" + rag_result["context"]
        )
        rag_result["sources"] = list(dict.fromkeys(facility_sources + rag_result.get("sources", [])))

    # Debug panel
    if debug_mode and rag_result["chunks"]:
        with st.expander("Debug: Retrieved RAG Chunks", expanded=False):
            st.markdown(
                '<div class="debug-panel-note">Chunk yang ditarik ditampilkan per kartu agar lebih ringkas dan tidak mengganggu layout utama.</div>',
                unsafe_allow_html=True,
            )
            for i, chunk in enumerate(rag_result["chunks"], 1):
                score = chunk.get('rerank_score', chunk.get('distance', '?'))
                if isinstance(score, float):
                    score = f"{score:.4f}"
                chunk_preview_html = (
                    '<div class="debug-chunk-card">'
                    '<div class="debug-chunk-meta">'
                    f'<span class="debug-chunk-title">Chunk {i}</span>'
                    f'<span class="debug-chip">{html.escape(chunk["source"])}</span>'
                    f'<span class="debug-chip">p.{chunk["page"]}</span>'
                    f'<span class="debug-chip">rerank score: {html.escape(str(score))}</span>'
                    '</div>'
                    f'<div class="debug-chunk-pre">{html.escape(chunk["text"][:900])}</div>'
                    '</div>'
                )
                st.markdown(chunk_preview_html, unsafe_allow_html=True)

    # Build chat history for multi-turn (limit to last 6 messages to avoid
    # old topics contaminating new answers)
    recent_messages = st.session_state.messages[-7:-1]  # last 6 msgs before the new one
    history = [
        {"role": m["role"], "content": m["content"]}
        for m in recent_messages
        if m["role"] in ("user", "assistant")
    ]

    # Stream response
    with st.chat_message("assistant", avatar=":material/support_agent:"):
        placeholder = st.empty()
        full_response = ""
        direct_response = _build_direct_schedule_answer(prompt, st.session_state.collection)

        try:
            if direct_response:
                full_response = direct_response
            else:
                for token in stream_chat_with_context(
                    user_query   = prompt,
                    context      = rag_result["context"],
                    chat_history = history,
                    model        = model_name,
                    temperature  = temperature,
                    max_tokens   = max_tokens,
                ):
                    full_response += token
                    placeholder.markdown(full_response + "◌")

                # If model returned nothing visible (all-think, empty), show fallback
                if not full_response.strip():
                    full_response = (
                        "Maaf sobat, saya tidak bisa menghasilkan respons untuk pertanyaan ini. "
                        "Coba ulangi atau perjelas pertanyaanmu ya!"
                    )

            # Output Guardrail (Fase 2.4)
            full_response = guard_output(full_response, context=rag_result.get("context", ""))
            placeholder.markdown(full_response)

            # Show sources
            if rag_result["sources"]:
                source_html = " ".join(
                    f'<span class="source-chip">{html.escape(str(s))}</span>'
                    for s in rag_result["sources"]
                )
                st.markdown(
                    f"<div style='margin-top:8px'>{source_html}</div>",
                    unsafe_allow_html=True,
                )

        except Exception as exc:
            full_response = (
                f"**Error komunikasi dengan Ollama:**\n\n```\n{exc}\n```\n\n"
                "Pastikan Ollama berjalan: `ollama serve`"
            )
            placeholder.markdown(full_response)

        # Show facility images if query is about facilities
        facility_imgs = _get_matching_facility_images(prompt)
        if facility_imgs:
            st.markdown("---")
            st.markdown('<div class="facility-section-title">Foto Fasilitas Terkait:</div>',
                        unsafe_allow_html=True)
            cols = st.columns(3)
            for idx, fimg in enumerate(facility_imgs):
                with cols[idx % 3]:
                    if os.path.exists(fimg["path"]):
                        st.image(fimg["path"], caption=fimg["name"], use_column_width=True)
                    else:
                        st.image(fimg["url"], caption=fimg["name"], use_column_width=True)

    st.session_state.messages.append(
        {
            "role":    "assistant",
            "content": full_response,
            "sources": rag_result.get("sources", []),
        }
    )
