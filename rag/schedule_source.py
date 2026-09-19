"""
rag/schedule_source.py — Extensible ScheduleSource interface and structured implementation.

Provides an abstract interface for schedule retrieval and an implementation
backed by data/structured/jadwal.jsonl. Future backends (e.g. SIAKAD API, SQLite)
can implement ScheduleSource seamlessly without changing callers.
"""

import os
import re
import json
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Set

from config import BASE_DIR


def _normalize_str(s: str) -> str:
    """Lowercase and strip punctuation/extra spaces for fuzzy matching."""
    if not s:
        return ""
    clean = re.sub(r"[^\w\s]", " ", s.lower())
    return re.sub(r"\s+", " ", clean).strip()


class ScheduleSource(ABC):
    """Abstract interface for schedule queries."""

    @abstractmethod
    def get_all(self) -> List[Dict[str, Any]]:
        """Return all schedule records."""
        pass

    @abstractmethod
    def search(
        self,
        prodi: Optional[str] = None,
        semester: Optional[str] = None,
        hari: Optional[str] = None,
        dosen: Optional[str] = None,
        mata_kuliah: Optional[str] = None,
        kode_mk: Optional[str] = None,
        ruang: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Filter schedule records matching provided criteria."""
        pass

    @abstractmethod
    def lookup_lecturer(
        self,
        lecturer_name: str,
        prodi: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Find courses taught by a lecturer."""
        pass

    @abstractmethod
    def lookup_course(
        self,
        course_name: str,
        prodi: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Find schedule entries for a specific course."""
        pass

    @abstractmethod
    def format_markdown_table(self, records: List[Dict[str, Any]]) -> str:
        """Render schedule records into a clean Markdown table."""
        pass


class StructuredFileScheduleSource(ScheduleSource):
    """
    ScheduleSource backed by data/structured/jadwal.jsonl.
    Enforces .rev precedence over non-rev for identical study programs.
    """

    def __init__(self, jsonl_path: Optional[str] = None):
        if jsonl_path is None:
            jsonl_path = os.path.join(BASE_DIR, "data", "structured", "jadwal.jsonl")
        self.jsonl_path = jsonl_path
        self._records: List[Dict[str, Any]] = []
        self._rev_prodis: Set[str] = set()
        self._load()

    def _load(self) -> None:
        if not os.path.exists(self.jsonl_path):
            self._records = []
            return

        raw_records = []
        with open(self.jsonl_path, mode="r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    raw_records.append(json.loads(line))

        # Identify which prodis have .rev versions
        for r in raw_records:
            if r.get("source_version") == "rev":
                self._rev_prodis.add(r.get("prodi_kode", ""))

        # Filter: if a prodi has .rev files, ignore non-rev records for that prodi
        filtered_records = []
        for r in raw_records:
            prodi = r.get("prodi_kode", "")
            ver = r.get("source_version", "non-rev")
            if prodi in self._rev_prodis and ver != "rev":
                continue
            filtered_records.append(r)

        self._records = filtered_records

    def get_all(self) -> List[Dict[str, Any]]:
        return list(self._records)

    def search(
        self,
        prodi: Optional[str] = None,
        semester: Optional[str] = None,
        hari: Optional[str] = None,
        dosen: Optional[str] = None,
        mata_kuliah: Optional[str] = None,
        kode_mk: Optional[str] = None,
        ruang: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        results = self._records

        if prodi:
            prodi_norm = _normalize_str(prodi)
            def _matches_prodi(r: Dict[str, Any]) -> bool:
                rk = _normalize_str(r.get("prodi_kode", ""))
                rf = _normalize_str(r.get("prodi_full", ""))
                if prodi_norm in ("inf", "ti", "informatika"):
                    return (rk in ("ti", "inf") or rf == "informatika") and "sistem" not in rf
                if prodi_norm in ("si", "sistem informasi"):
                    return rk == "si" or rf == "sistem informasi"
                if prodi_norm in ("ts", "sipil", "teknik sipil"):
                    return rk == "ts" or "sipil" in rf
                return prodi_norm == rk or prodi_norm == rf or re.search(r"\b" + re.escape(prodi_norm) + r"\b", rf) is not None

            results = [r for r in results if _matches_prodi(r)]

        if semester:
            sem_norm = _normalize_str(semester)
            results = [
                r for r in results
                if sem_norm == _normalize_str(r.get("semester", ""))
            ]

        if hari:
            hari_norm = _normalize_str(hari)
            results = [
                r for r in results
                if hari_norm == _normalize_str(r.get("hari", ""))
            ]

        if dosen:
            dosen_norm = _normalize_str(dosen)
            results = [
                r for r in results
                if any(dosen_norm in _normalize_str(d) for d in r.get("dosen", []))
            ]

        if mata_kuliah:
            mk_norm = _normalize_str(mata_kuliah)
            results = [
                r for r in results
                if mk_norm in _normalize_str(r.get("mata_kuliah", ""))
            ]

        if kode_mk:
            kmk_norm = _normalize_str(kode_mk)
            results = [
                r for r in results
                if kmk_norm == _normalize_str(r.get("kode_mk", ""))
            ]

        if ruang:
            ruang_norm = _normalize_str(ruang)
            results = [
                r for r in results
                if ruang_norm in _normalize_str(r.get("ruang", ""))
            ]

        return results

    def lookup_lecturer(
        self,
        lecturer_name: str,
        prodi: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        name_norm = _normalize_str(lecturer_name)
        if not name_norm:
            return []
        candidates = []
        for r in self._records:
            if prodi:
                p_norm = _normalize_str(prodi)
                if p_norm not in _normalize_str(r.get("prodi_kode", "")) and p_norm not in _normalize_str(r.get("prodi_full", "")):
                    continue
            for d in r.get("dosen", []):
                d_norm = _normalize_str(d)
                if d_norm and (name_norm in d_norm or d_norm in name_norm or all(part in d_norm for part in name_norm.split() if len(part) > 2)):
                    candidates.append(r)
                    break
        return candidates

    def lookup_course(
        self,
        course_name: str,
        prodi: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        c_norm = _normalize_str(course_name)
        if not c_norm:
            return []
        candidates = []
        for r in self._records:
            if prodi:
                p_norm = _normalize_str(prodi)
                if p_norm not in _normalize_str(r.get("prodi_kode", "")) and p_norm not in _normalize_str(r.get("prodi_full", "")):
                    continue
            mk_norm = _normalize_str(r.get("mata_kuliah", ""))
            if mk_norm and (c_norm == mk_norm or c_norm in mk_norm or (len(mk_norm) >= 4 and mk_norm in c_norm)):
                candidates.append(r)
        return candidates

    def format_markdown_table(self, records: List[Dict[str, Any]]) -> str:
        """
        Format records into the standard Markdown table:
        Hari | Jam | Mata Kuliah | Kode | SKS | Kelas | Ruang | Dosen
        """
        if not records:
            return "Tidak ada jadwal yang sesuai dengan kriteria pencarian."

        header = "| Hari | Jam | Mata Kuliah | Kode | SKS | Kelas | Ruang | Dosen |"
        sep = "| :--- | :--- | :--- | :--- | :---: | :---: | :--- | :--- |"
        rows = []
        has_needs_review = False

        for r in records:
            hari = r.get("hari") or "-"
            jm = r.get("jam_mulai", "-")
            js = r.get("jam_selesai", "-")
            jam = f"{jm} - {js}" if jm != "-" and js != "-" else "-"
            mk = r.get("mata_kuliah") or "-"
            kode = r.get("kode_mk") or "-"
            sks = str(r.get("sks")) if r.get("sks") is not None else "-"
            kls = r.get("kelas") or "-"
            ruang = r.get("ruang") or "-"
            dosen_list = r.get("dosen") or []
            dosen_str = ", ".join(dosen_list) if dosen_list else "-"

            if r.get("needs_review"):
                has_needs_review = True

            rows.append(f"| {hari} | {jam} | {mk} | {kode} | {sks} | {kls} | {ruang} | {dosen_str} |")

        table_text = "\n".join([header, sep] + rows)

        if has_needs_review:
            table_text += (
                "\n\n*Catatan: Data ini hasil pembacaan otomatis dari dokumen, "
                "mohon dicek ulang di jadwal resmi.*"
            )

        return table_text


_default_schedule_source: Optional[ScheduleSource] = None


def get_schedule_source() -> ScheduleSource:
    """Module-level singleton provider for ScheduleSource."""
    global _default_schedule_source
    if _default_schedule_source is None:
        _default_schedule_source = StructuredFileScheduleSource()
    return _default_schedule_source
