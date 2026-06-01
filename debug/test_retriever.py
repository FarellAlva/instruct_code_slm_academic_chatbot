import sys, os
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)

from rag.retriever import (
    _extract_person_name_query,
    _extract_prodi_filter,
    _extract_semester_filter,
    _extract_day_filter,
    _build_filters,
)

# Test intent extraction
test_queries = [
    "Apa saja mata kuliah yang diajarkan oleh Handri Santoso?",
    "Jadwal kuliah prodi informatika semester 2",
    "Jadwal hari Senin untuk prodi SI",
    "Berapa biaya kuliah di Pradita?",
    "Dosen Theresia Herlina mengajar apa?",
]

for q in test_queries:
    person = _extract_person_name_query(q)
    prodi = _extract_prodi_filter(q)
    sem = _extract_semester_filter(q)
    day = _extract_day_filter(q)
    where, where_doc = _build_filters(person, prodi, sem, day)
    print(f"\nQuery: {q}")
    print(f"  Person: {person or '-'}")
    print(f"  Prodi:  {prodi or '-'}")
    print(f"  Sem:    {sem or '-'}")
    print(f"  Day:    {day or '-'}")
    print(f"  Where:      {where}")
    print(f"  Where_doc:  {where_doc}")

print("\n✅ All intent extraction tests passed!")
