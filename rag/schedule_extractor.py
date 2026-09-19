"""
rag/schedule_extractor.py — Precision table extraction from schedule PDFs using PyMuPDF find_tables().

Transforms university schedule PDFs into clean structured records:
- Output 1: data/structured/jadwal.jsonl (1 JSON record per schedule entry)
- Output 2: data/structured/jadwal_review.csv (entries failing validation or requiring review)
"""

import os
import re
import csv
import json
import glob
import hashlib
from typing import Dict, List, Any, Optional, Tuple

import fitz  # PyMuPDF

PRODI_MAP: Dict[str, str] = {
    "TI": "Informatika",
    "INF": "Informatika",
    "SI": "Sistem Informasi",
    "PAR": "Pariwisata",
    "PWK": "Perencanaan Wilayah dan Kota",
    "AR": "Arsitektur",
    "ARS": "Arsitektur",
    "TS": "Teknik Sipil",
    "DKV": "Desain Komunikasi Visual",
    "DI": "Desain Interior",
    "SK": "Seni Kuliner",
    "MB": "Manajemen Bisnis",
    "MR": "Manajemen Bisnis / Retail",
    "AK": "Akuntansi",
    "F&B": "Food & Beverage",
    "MKDU": "Mata Kuliah Dasar Umum",
}

VALID_DAYS = {"Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu"}


def parse_time_range(jam_raw: str) -> Tuple[Optional[str], Optional[str], bool]:
    """
    Parse time range string (e.g. '08.25 - 11.05', '10.15 -12.00') into (start, end, is_valid).
    """
    if not jam_raw:
        return None, None, False

    clean = re.sub(r"\s+", "", jam_raw.replace(":", "."))
    match = re.search(r"(\d{1,2}\.\d{2})-(\d{1,2}\.\d{2})", clean)
    if not match:
        return None, None, False

    start, end = match.group(1), match.group(2)
    # Pad to HH.MM if needed
    if len(start.split(".")[0]) == 1:
        start = "0" + start
    if len(end.split(".")[0]) == 1:
        end = "0" + end

    try:
        sh, sm = map(int, start.split("."))
        eh, em = map(int, end.split("."))
        start_min = sh * 60 + sm
        end_min = eh * 60 + em
        is_valid = (start_min < end_min)
        return start, end, is_valid
    except ValueError:
        return start, end, False


def parse_lecturers(dosen_raw: str) -> List[str]:
    """Parse and normalize lecturer names from raw cell string."""
    if not dosen_raw or not dosen_raw.strip():
        return []

    lines = [re.sub(r"\s+", " ", l).strip() for l in dosen_raw.split("\n")]
    lecturers = []
    for l in lines:
        if not l or l == "-":
            continue
        # Split on slash if used as separator between distinct people
        parts = [p.strip() for p in l.split("/") if p.strip()]
        for p in parts:
            if len(p) > 2 and p not in lecturers:
                lecturers.append(p)
    return lecturers


def extract_table_from_page(page: fitz.Page) -> List[List[Optional[str]]]:
    """Extract table rows from a page using PyMuPDF find_tables."""
    tabs = page.find_tables()
    if not tabs.tables:
        return []
    # Use first main table on page
    return tabs.tables[0].extract()


def process_all_schedules(
    jadwal_dir: str = "data/jadwal",
    output_dir: str = "data/structured",
) -> Dict[str, Any]:
    """
    Extract and validate all 13 schedule PDFs.
    Outputs:
      - output_dir/jadwal.jsonl
      - output_dir/jadwal_review.csv
    """
    os.makedirs(output_dir, exist_ok=True)
    pdf_files = sorted(glob.glob(os.path.join(jadwal_dir, "*.pdf")))

    all_records: List[Dict[str, Any]] = []
    review_records: List[Dict[str, Any]] = []
    file_summaries: List[Dict[str, Any]] = []

    global_idx = 0

    for pdf_path in pdf_files:
        fname = os.path.basename(pdf_path)
        with open(pdf_path, "rb") as fp:
            file_hash = hashlib.sha256(fp.read()).hexdigest()

        source_version = "rev" if ".rev." in fname.lower() else "non-rev"
        doc = fitz.open(pdf_path)

        file_total_rows = 0
        file_review_rows = 0

        for pno, page in enumerate(doc, 1):
            raw_rows = extract_table_from_page(page)
            if not raw_rows:
                continue

            # Identify header row & build column mapping
            col_map = {}
            for r_idx, row in enumerate(raw_rows):
                if not col_map and any(c and "hari" in str(c).lower() for c in row):
                    for c_idx, c in enumerate(row):
                        if not c:
                            continue
                        cl = re.sub(r"\s+", " ", str(c).strip().lower())
                        if "hari" in cl:
                            col_map["hari"] = c_idx
                        elif "jam" in cl:
                            col_map["jam"] = c_idx
                        elif "smt" in cl or "semester" in cl:
                            col_map["smt"] = c_idx
                        elif "prodi" in cl:
                            col_map["prodi"] = c_idx
                        elif "kmk" in cl or "kode" in cl:
                            col_map["kmk"] = c_idx
                        elif "mata kuliah" in cl or "matakuliah" in cl:
                            col_map["mata_kuliah"] = c_idx
                        elif "sks" in cl:
                            col_map["sks"] = c_idx
                        elif "kls" in cl or "kelas" in cl:
                            col_map["kelas"] = c_idx
                        elif "dosen" in cl or "pengajar" in cl:
                            col_map["dosen"] = c_idx
                        elif "ruang" in cl:
                            col_map["ruang"] = c_idx
                        elif "catatan" in cl or "ket" in cl:
                            col_map["catatan"] = c_idx
                    continue

                if not col_map:
                    continue

                # Detect candidate schedule row
                no_cell = str(row[0]).strip() if row and row[0] is not None else ""
                hari_cell = (
                    str(row[col_map["hari"]]).strip()
                    if "hari" in col_map and col_map["hari"] < len(row) and row[col_map["hari"]]
                    else ""
                )

                if no_cell.isdigit() or hari_cell in VALID_DAYS:
                    global_idx += 1
                    file_total_rows += 1

                    # Extract raw cell values
                    def _get_val(key: str) -> str:
                        if key in col_map and col_map[key] < len(row) and row[col_map[key]] is not None:
                            return str(row[col_map[key]]).strip()
                        return ""

                    hari_val = _get_val("hari")
                    jam_val = _get_val("jam")
                    smt_val = _get_val("smt")
                    prodi_val = _get_val("prodi")
                    kmk_val = _get_val("kmk")
                    mk_val = _get_val("mata_kuliah")
                    sks_val = _get_val("sks")
                    kls_val = _get_val("kelas")
                    dosen_val = _get_val("dosen")
                    ruang_val = _get_val("ruang")
                    catatan_val = _get_val("catatan")

                    # Parse & normalize
                    start_time, end_time, time_valid = parse_time_range(jam_val)
                    lecturers = parse_lecturers(dosen_val)

                    # Clean room (replace internal newlines with ' / ')
                    ruang_clean = " / ".join(
                        part.strip() for part in ruang_val.split("\n") if part.strip()
                    ) if ruang_val else "-"

                    # Clean notes
                    catatan_clean = " ".join(
                        part.strip() for part in catatan_val.split("\n") if part.strip()
                    )

                    # Clean course title
                    mk_clean = re.sub(r"\s+", " ", mk_val).strip()

                    # SKS as integer
                    sks_int = None
                    if sks_val and sks_val.isdigit():
                        sks_int = int(sks_val)

                    # Map prodi full name
                    prodi_code_clean = prodi_val.upper().strip() if prodi_val else ""
                    prodi_full = PRODI_MAP.get(prodi_code_clean, prodi_code_clean)

                    # Validation
                    validation_errors = []
                    if hari_val not in VALID_DAYS:
                        validation_errors.append(f"invalid_day:{hari_val}")
                    if not time_valid:
                        validation_errors.append(f"invalid_time_range:{jam_val}")
                    if not mk_clean:
                        validation_errors.append("missing_course_name")

                    needs_review = len(validation_errors) > 0
                    confidence = 1.0 if not needs_review else 0.5

                    if needs_review:
                        file_review_rows += 1

                    # Assemble canonical record
                    record_id = f"SCHED-{prodi_code_clean or 'GEN'}-{global_idx:04d}"
                    raw_text_repr = " | ".join(str(c or "") for c in row)

                    record = {
                        "id": record_id,
                        "source_file": fname,
                        "source_version": source_version,
                        "file_hash": file_hash,
                        "page": pno,
                        "row_index": r_idx,
                        "prodi_kode": prodi_code_clean,
                        "prodi_full": prodi_full,
                        "semester": smt_val,
                        "periode": "Genap 2025/2026",
                        "tahun_ajaran": "2025/2026",
                        "hari": hari_val,
                        "jam_mulai": start_time or "-",
                        "jam_selesai": end_time or "-",
                        "kode_mk": kmk_val,
                        "mata_kuliah": mk_clean,
                        "sks": sks_int,
                        "kelas": kls_val,
                        "ruang": ruang_clean,
                        "dosen": lecturers,
                        "catatan": catatan_clean,
                        "raw_text": raw_text_repr,
                        "parse_confidence": confidence,
                        "needs_review": needs_review,
                        "validation_notes": "; ".join(validation_errors) if validation_errors else "valid",
                    }

                    all_records.append(record)

                    if needs_review:
                        review_records.append(record)

        file_summaries.append(
            {
                "file": fname,
                "version": source_version,
                "total_rows": file_total_rows,
                "needs_review_rows": file_review_rows,
            }
        )

    # 1. Write structured JSONL
    jsonl_path = os.path.join(output_dir, "jadwal.jsonl")
    with open(jsonl_path, mode="w", encoding="utf-8") as f:
        for rec in all_records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    # 2. Write review CSV
    csv_path = os.path.join(output_dir, "jadwal_review.csv")
    csv_cols = [
        "id",
        "source_file",
        "page",
        "row_index",
        "hari",
        "jam_mulai",
        "jam_selesai",
        "prodi_kode",
        "semester",
        "mata_kuliah",
        "ruang",
        "dosen",
        "validation_notes",
        "raw_text",
    ]
    with open(csv_path, mode="w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=csv_cols)
        writer.writeheader()
        for r in review_records:
            row_dict = {k: r.get(k, "") for k in csv_cols}
            if isinstance(row_dict["dosen"], list):
                row_dict["dosen"] = "; ".join(row_dict["dosen"])
            writer.writerow(row_dict)

    # Room collision analysis
    collisions = check_room_collisions(all_records)

    return {
        "total_records": len(all_records),
        "valid_records": len(all_records) - len(review_records),
        "needs_review_records": len(review_records),
        "files_processed": len(file_summaries),
        "file_summaries": file_summaries,
        "collisions_detected": len(collisions),
        "collisions": collisions,
        "jsonl_path": jsonl_path,
        "review_csv_path": csv_path,
    }


def check_room_collisions(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Detect overlapping schedules in the same room on the same day."""
    room_day_map: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
    collisions: List[Dict[str, Any]] = []

    for r in records:
        ruang = r.get("ruang", "").strip()
        hari = r.get("hari", "").strip()
        jm = r.get("jam_mulai", "").strip()
        js = r.get("jam_selesai", "").strip()

        # Skip virtual/unassigned rooms or missing times
        if not ruang or ruang in ("-", "", "None") or not hari or jm == "-" or js == "-":
            continue

        try:
            sm = int(jm.split(".")[0]) * 60 + int(jm.split(".")[1])
            em = int(js.split(".")[0]) * 60 + int(js.split(".")[1])
        except (ValueError, IndexError):
            continue

        # Check against existing entries for this (room, day)
        key = (ruang, hari)
        if key in room_day_map:
            for existing in room_day_map[key]:
                # Overlap check
                if not (em <= existing["sm"] or sm >= existing["em"]):
                    # If it's a combined class (e.g. gabung SI + PAR), notes will mention it
                    collisions.append(
                        {
                            "ruang": ruang,
                            "hari": hari,
                            "class_1": f"{r['mata_kuliah']} ({r['prodi_kode']} Smt {r['semester']}, {jm}-{js})",
                            "class_2": f"{existing['rec']['mata_kuliah']} ({existing['rec']['prodi_kode']} Smt {existing['rec']['semester']}, {existing['rec']['jam_mulai']}-{existing['rec']['jam_selesai']})",
                            "catatan_1": r.get("catatan", ""),
                            "catatan_2": existing["rec"].get("catatan", ""),
                        }
                    )
        else:
            room_day_map[key] = []

        room_day_map[key].append({"sm": sm, "em": em, "rec": r})

    return collisions


if __name__ == "__main__":
    result = process_all_schedules()
    print("=" * 60)
    print("  Pradita University — Schedule Extraction Summary")
    print("=" * 60)
    print(f"Files Processed        : {result['files_processed']}")
    print(f"Total Extracted Rows   : {result['total_records']}")
    print(f"Valid Rows             : {result['valid_records']}")
    print(f"Needs Review Rows      : {result['needs_review_records']}")
    print(f"Potential Collisions   : {result['collisions_detected']}")
    print(f"Output JSONL           : {result['jsonl_path']}")
    print(f"Output Review CSV      : {result['review_csv_path']}")
    print("-" * 60)
    for fs in result["file_summaries"]:
        print(f"  {fs['file'][:35]:35s} | ver: {fs['version']:7s} | total: {fs['total_rows']:2d} | review: {fs['needs_review_rows']}")
    print("=" * 60)
