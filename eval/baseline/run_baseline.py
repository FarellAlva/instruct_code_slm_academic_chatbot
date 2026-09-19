"""
eval/baseline/run_baseline.py
=============================
Baseline evaluation runner for Adita RAG v1 (Fase 0.2).
Evaluates 35 queries:
- 15 Ground Truth queries (from eval/ground_truth.csv)
- 5 Audit Quick Test queries
- 15 Custom queries across prodi, dosen, kode MK, ruang, biaya, beasiswa, fasilitas, out-of-scope

Saves results to:
- eval/baseline/baseline_results.csv
- eval/baseline/baseline_results.json
"""

import os
import sys

# Workaround for NumPy 2.x optional binary extensions in pandas
sys.modules['bottleneck'] = None
sys.modules['numexpr'] = None

import csv
import json
import time
import re

# Add project root to sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from config import (
    DEFAULT_MODEL,
    DEFAULT_TEMPERATURE,
    DEFAULT_MAX_TOKENS,
    DEFAULT_TOP_P,
    TOP_K_RETRIEVAL,
)
from rag.retriever import retrieve_context
from rag.scraper import FACILITY_IMAGES
from llm.ollama_client import chat_with_context

# ─── App Logic Replicated for Exact Pipeline Parity ───────────────────────────

FACILITY_KEYWORDS = [
    "fasilitas", "facility", "facilities", "gedung", "building", "kampus",
    "campus", "lab", "laboratorium", "perpustakaan", "library", "auditorium",
    "classroom", "ruang kelas", "kantin", "canteen", "asrama", "boarding",
    "shuttle", "kolam renang", "swimming", "gym", "sport", "olahraga",
    "vr room", "podcast", "workshop", "kitchen", "hotel", "lounge",
]

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
    img_stop_words = {"pradita", "university", "universitas", "kampus", "ada",
                      "apakah", "apa", "yang", "dari", "dan", "ini", "itu"}

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

_LECTURER_QUERY_STOP_WORDS = {
    "siapa", "itu", "apa", "apakah", "ada", "di", "ke", "dari", "yang", "dan",
    "untuk", "jadwal", "berikan", "saya", "tolong", "bisa", "adalah", "ini",
    "beliau", "ngajar", "mengajar", "ampu", "mengampu", "mata", "kuliah",
    "semester", "prodi", "jurusan", "kelas", "ruang", "jam", "hari", "berapa",
    "bagaimana", "dengan", "tentang", "pak", "bu", "bapak", "ibu", "ajarkan",
    "ajar", "saja", "dosen", "genap", "ganjil", "periode", "tahun",
}
_DAY_ORDER = {"Senin": 0, "Selasa": 1, "Rabu": 2, "Kamis": 3, "Jumat": 4, "Sabtu": 5}
_ROMAN_TO_INT = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7, "VIII": 8}

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
    return re.sub(r"\s+", " ", cleaned).strip(" .,;")

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
        elif clean.startswith("Hari:"):
            entry["hari"] = clean.split(":", 1)[1].strip().rstrip(".")
        elif clean.startswith("Jam:"):
            entry["jam"] = clean.split(":", 1)[1].strip().rstrip(".")
        elif clean.startswith("Mata kuliah:"):
            entry["mata_kuliah"] = clean.split(":", 1)[1].strip().rstrip(".")
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

def _build_direct_lecturer_schedule_answer(query: str, rag_result: dict) -> str:
    lecturer_query = _extract_lecturer_query_name(query)
    if not lecturer_query:
        return ""
    lowered = query.lower()
    if not any(token in lowered for token in ("mengajar", "ngajar", "mata kuliah", "ampu", "jadwal", "kelas", "hari", "jam")):
        return ""
    lecturer_target = _normalize_lookup_text(lecturer_query)
    entries = []
    for chunk in rag_result.get("chunks", []):
        entry = _parse_schedule_chunk_entry(chunk["text"])
        if not entry:
            continue
        matched_lecturer = ""
        for lecturer in entry.get("lecturers", []):
            normalized = _normalize_lookup_text(lecturer)
            if lecturer_target in normalized or normalized in lecturer_target:
                matched_lecturer = lecturer
                break
        if not matched_lecturer:
            continue
        entry["lecturer"] = matched_lecturer
        entries.append(entry)
    if not entries:
        return (
            f"Saya belum menemukan entri jadwal yang secara eksplisit menuliskan **{lecturer_query}** "
            "pada chunk yang berhasil diambil. Jadi saya tidak akan menebak mata kuliahnya."
        )
    deduped = []
    seen = set()
    for entry in entries:
        key = (entry.get("program_studi", ""), entry.get("hari", ""), entry.get("jam", ""), entry.get("mata_kuliah", ""))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(entry)
    header = f"Ini data jadwal yang secara eksplisit menuliskan **{deduped[0]['lecturer']}** di database saat ini:"
    table_lines = [
        "| Hari | Jam | Mata Kuliah | Program Studi | Semester | Ruang |",
        "|------|-----|-------------|---------------|----------|-------|",
    ]
    for entry in deduped:
        table_lines.append(
            f"| {entry.get('hari', '-')} | {entry.get('jam', '-')} | {entry.get('mata_kuliah', '-')} | "
            f"{entry.get('program_studi', '-')} | {entry.get('semester', '-')} | {entry.get('ruang', '-')} |"
        )
    return "\n\n".join([header, "\n".join(table_lines)])


# ─── Main Evaluation Execution ────────────────────────────────────────────────

def main():
    eval_dir = os.path.join(BASE_DIR, "eval", "baseline")
    os.makedirs(eval_dir, exist_ok=True)
    questions_file = os.path.join(eval_dir, "baseline_questions.csv")
    results_csv = os.path.join(eval_dir, "baseline_results.csv")
    results_json = os.path.join(eval_dir, "baseline_results.json")

    print(f"=== Adita RAG Baseline Evaluation (Fase 0.2) ===")
    print(f"Model: {DEFAULT_MODEL}")
    print(f"Loading questions from: {questions_file}")

    with open(questions_file, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        questions = list(reader)

    print(f"Total questions to evaluate: {len(questions)}\n")

    results = []

    for idx, q_row in enumerate(questions, 1):
        q_id = q_row["id"]
        q_type = q_row["type"]
        q_cat = q_row["category"]
        query = q_row["question"]

        print(f"[{idx}/{len(questions)}] (ID: {q_id}) [{q_type}] {query}")

        # 1. Retrieval
        t_ret_start = time.perf_counter()
        rag_result = retrieve_context(query=query, top_k=TOP_K_RETRIEVAL)
        ret_latency = time.perf_counter() - t_ret_start

        # Facility context injection
        fac_ctx, _ = _build_facility_context(query)
        full_context = rag_result["context"]
        if fac_ctx:
            full_context = fac_ctx if not full_context else f"{fac_ctx}\n\n---\n\n{full_context}"

        # Images attached
        images = _get_matching_facility_images(query)

        # 2. Check direct bypass
        direct_resp = _build_direct_lecturer_schedule_answer(query, rag_result)
        hit_bypass = False
        t_llm_start = time.perf_counter()

        if direct_resp:
            hit_bypass = True
            response_text = direct_resp
            llm_latency = 0.0
            print(f"    -> Direct bypass triggered! (Refusal or answer generated without LLM)")
        else:
            try:
                response_text = chat_with_context(
                    user_query=query,
                    context=full_context,
                    model=DEFAULT_MODEL,
                    temperature=DEFAULT_TEMPERATURE,
                    max_tokens=DEFAULT_MAX_TOKENS,
                    top_p=DEFAULT_TOP_P,
                )
            except Exception as e:
                response_text = f"[ERROR: {str(e)}]"
            llm_latency = time.perf_counter() - t_llm_start

        total_latency = ret_latency + llm_latency

        # Extract top chunk info
        chunks = rag_result.get("chunks", [])
        top_chunk_source = chunks[0]["source"] if chunks else "none"
        top_chunk_page = chunks[0].get("page", 0) if chunks else 0
        top_chunk_score = chunks[0].get("rerank_score", 0.0) if chunks else 0.0

        item_result = {
            "id": int(q_id),
            "type": q_type,
            "category": q_cat,
            "question": query,
            "hit_direct_bypass": hit_bypass,
            "num_chunks": len(chunks),
            "top_chunk_source": top_chunk_source,
            "top_chunk_page": top_chunk_page,
            "top_chunk_score": round(float(top_chunk_score), 4),
            "retrieval_latency_s": round(ret_latency, 3),
            "llm_latency_s": round(llm_latency, 3),
            "total_latency_s": round(total_latency, 3),
            "num_images": len(images),
            "images_attached": [img["name"] for img in images],
            "response_text": response_text.strip(),
            "retrieved_chunks": [
                {
                    "rank": r_idx + 1,
                    "id": c.get("id", ""),
                    "source": c.get("source", ""),
                    "page": c.get("page", 0),
                    "rerank_score": round(float(c.get("rerank_score", 0.0)), 4) if "rerank_score" in c else None,
                    "text_preview": c.get("text", "")[:150],
                }
                for r_idx, c in enumerate(chunks)
            ],
        }
        results.append(item_result)
        print(f"    Done in {total_latency:.2f}s (ret: {ret_latency:.2f}s, llm: {llm_latency:.2f}s) | chunks: {len(chunks)} | images: {len(images)}")

        # Checkpoint JSON after every item
        with open(results_json, "w", encoding="utf-8") as jf:
            json.dump(results, jf, ensure_ascii=False, indent=2)

    # Save to CSV
    csv_fieldnames = [
        "id", "type", "category", "question", "hit_direct_bypass",
        "num_chunks", "top_chunk_source", "top_chunk_page", "top_chunk_score",
        "retrieval_latency_s", "llm_latency_s", "total_latency_s",
        "num_images", "images_attached", "response_text"
    ]
    with open(results_csv, "w", encoding="utf-8", newline="") as cf:
        writer = csv.DictWriter(cf, fieldnames=csv_fieldnames)
        writer.writeheader()
        for r in results:
            row_copy = dict(r)
            row_copy.pop("retrieved_chunks", None)
            row_copy["images_attached"] = "; ".join(row_copy["images_attached"])
            # Clean newline in response_text for single line in CSV
            row_copy["response_text"] = row_copy["response_text"].replace("\r", "").replace("\n", " \\n ")
            writer.writerow(row_copy)

    print(f"\n=== Baseline Evaluation Completed ===")
    print(f"Results CSV: {results_csv}")
    print(f"Results JSON: {results_json}")

    # Summary Stats
    avg_total_lat = sum(r["total_latency_s"] for r in results) / len(results)
    avg_ret_lat = sum(r["retrieval_latency_s"] for r in results) / len(results)
    avg_llm_lat = sum(r["llm_latency_s"] for r in results) / len(results)
    bypass_count = sum(1 for r in results if r["hit_direct_bypass"])
    image_attached_count = sum(1 for r in results if r["num_images"] > 0)

    print(f"\n--- Baseline Summary ---")
    print(f"Total Queries: {len(results)}")
    print(f"Direct Bypass Triggered: {bypass_count} / {len(results)}")
    print(f"Queries with Facility Images: {image_attached_count} / {len(results)}")
    print(f"Average Total Latency: {avg_total_lat:.2f} s")
    print(f"Average Retrieval Latency: {avg_ret_lat:.2f} s")
    print(f"Average LLM Latency: {avg_llm_lat:.2f} s")

if __name__ == "__main__":
    main()
