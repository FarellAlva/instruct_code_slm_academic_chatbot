"""
eval/generate_schedule_golden_set.py — Automated Golden Set generator and evaluator for structured schedule queries.

Evaluates deterministic exact-match accuracy without LLM:
1. prodi x semester x hari -> exact course list
2. dosen -> exact list of taught courses
3. kode_mk / course -> exact room and schedule

Target metric (Fase 3): exact-match >= 98%.
"""

import os
import sys
import re
import csv
import json

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Dict, List, Any, Tuple
from rag.schedule_source import get_schedule_source
from rag.entity_index import normalize_title, normalize_course_name, normalize_lookup


def generate_and_evaluate_golden_set(
    output_csv: str = "eval/schedule_golden_set.csv",
) -> Dict[str, Any]:
    sched_src = get_schedule_source()
    records = sched_src.get_all()

    test_cases: List[Dict[str, Any]] = []

    # 1. Category A: (prodi, semester, hari) combinations
    prodi_sem_day: Dict[Tuple[str, str, str], List[str]] = {}
    for r in records:
        p = r.get("prodi_kode")
        s = r.get("semester")
        h = r.get("hari")
        mk = r.get("mata_kuliah")
        if p and s and h and mk:
            key = (p, s, h)
            prodi_sem_day.setdefault(key, [])
            if mk not in prodi_sem_day[key]:
                prodi_sem_day[key].append(mk)

    case_id = 1
    # Sample up to 40 distinct prodi-semester-day triplets
    for (p, s, h), expected_courses in sorted(prodi_sem_day.items())[:40]:
        query = f"Jadwal kuliah {p} semester {s} hari {h}"
        test_cases.append(
            {
                "id": f"GOLD-A-{case_id:03d}",
                "type": "prodi_sem_day",
                "query": query,
                "target_prodi": p,
                "target_semester": s,
                "target_day": h,
                "target_entity": "",
                "expected_items": ";".join(expected_courses),
            }
        )
        case_id += 1

    # 2. Category B: Lecturer -> courses taught
    lecturer_courses: Dict[str, List[str]] = {}
    for r in records:
        mk = r.get("mata_kuliah")
        for d in r.get("dosen", []):
            if d and mk:
                lecturer_courses.setdefault(d, [])
                if mk not in lecturer_courses[d]:
                    lecturer_courses[d].append(mk)

    # Sample top 30 lecturers with at least 1 course
    case_id = 1
    for d, expected_courses in sorted(lecturer_courses.items())[:30]:
        clean_name = normalize_title(d)
        query = f"Mata kuliah apa saja yang diajar oleh {d}?"
        test_cases.append(
            {
                "id": f"GOLD-B-{case_id:03d}",
                "type": "lecturer_courses",
                "query": query,
                "target_prodi": "",
                "target_semester": "",
                "target_day": "",
                "target_entity": d,
                "expected_items": ";".join(expected_courses),
            }
        )
        case_id += 1

    # 3. Category C: Course code -> schedule & room
    code_info: Dict[str, Dict[str, Any]] = {}
    for r in records:
        kmk = r.get("kode_mk")
        if kmk and len(kmk) >= 5 and kmk not in code_info:
            code_info[kmk] = {
                "mata_kuliah": r.get("mata_kuliah"),
                "ruang": r.get("ruang"),
                "hari": r.get("hari"),
            }

    case_id = 1
    for kmk, info in sorted(code_info.items())[:30]:
        query = f"Mata kuliah kode {kmk} jadwal dan ruangannya di mana?"
        test_cases.append(
            {
                "id": f"GOLD-C-{case_id:03d}",
                "type": "code_lookup",
                "query": query,
                "target_prodi": "",
                "target_semester": "",
                "target_day": "",
                "target_entity": kmk,
                "expected_items": f"{info['mata_kuliah']} | {info['ruang']} | {info['hari']}",
            }
        )
        case_id += 1

    # Write golden set CSV
    os.makedirs(os.path.dirname(output_csv) or ".", exist_ok=True)
    fieldnames = [
        "id",
        "type",
        "query",
        "target_prodi",
        "target_semester",
        "target_day",
        "target_entity",
        "expected_items",
    ]
    with open(output_csv, mode="w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(test_cases)

    # Evaluate exact match
    exact_matches = 0
    total = len(test_cases)
    cat_stats: Dict[str, Dict[str, int]] = {}

    for tc in test_cases:
        ctype = tc["type"]
        cat_stats.setdefault(ctype, {"total": 0, "matched": 0})
        cat_stats[ctype]["total"] += 1

        is_match = False

        if ctype == "prodi_sem_day":
            recs = sched_src.search(
                prodi=tc["target_prodi"],
                semester=tc["target_semester"],
                hari=tc["target_day"],
            )
            found_courses = {r.get("mata_kuliah") for r in recs if r.get("mata_kuliah")}
            expected_set = set(tc["expected_items"].split(";"))
            if expected_set.issubset(found_courses):
                is_match = True

        elif ctype == "lecturer_courses":
            recs = sched_src.lookup_lecturer(tc["target_entity"])
            found_courses = {r.get("mata_kuliah") for r in recs if r.get("mata_kuliah")}
            expected_set = set(tc["expected_items"].split(";"))
            if expected_set.issubset(found_courses):
                is_match = True

        elif ctype == "code_lookup":
            recs = sched_src.search(kode_mk=tc["target_entity"])
            if recs:
                first = recs[0]
                exp_mk, exp_ruang, exp_hari = [x.strip() for x in tc["expected_items"].split("|")]
                if first.get("mata_kuliah") == exp_mk and first.get("hari") == exp_hari:
                    is_match = True

        if is_match:
            exact_matches += 1
            cat_stats[ctype]["matched"] += 1

    accuracy = (exact_matches / total) * 100 if total else 0.0

    return {
        "total_cases": total,
        "exact_matches": exact_matches,
        "accuracy_pct": accuracy,
        "category_stats": cat_stats,
        "csv_path": output_csv,
    }


if __name__ == "__main__":
    res = generate_and_evaluate_golden_set()
    print("=" * 60)
    print("  Pradita University — Schedule Golden Set Evaluation")
    print("=" * 60)
    print(f"Total Test Cases      : {res['total_cases']}")
    print(f"Exact Matches         : {res['exact_matches']}")
    print(f"Exact Match Accuracy  : {res['accuracy_pct']:.2f}% (Target: >= 98.0%)")
    print("-" * 60)
    for cat, s in res["category_stats"].items():
        cat_pct = (s["matched"] / s["total"]) * 100
        print(f"  {cat:22s} | Matched: {s['matched']:2d}/{s['total']:2d} ({cat_pct:.1f}%)")
    print("=" * 60)
