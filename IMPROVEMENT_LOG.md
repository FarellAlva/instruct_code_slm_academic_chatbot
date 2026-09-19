# IMPROVEMENT LOG — SISTEM RAG "ADITA" (PRADITA UNIVERSITY)

Dokumen ini mencatat seluruh proses perbaikan sistem RAG secara bertahap, terukur, dan berbasis bukti (evidence-based).

---

## FASE 0 — Baseline & Verifikasi

### 1. Ringkasan yang Dikerjakan
Fase 0 telah diselesaikan dengan membangun fondasi pengujian offline, mencadangkan seluruh data vektor, memverifikasi 4 asumsi teknis kritis hasil audit, serta menjalankan evaluasi baseline terhadap 35 kueri (15 ground truth, 5 uji cepat audit, dan 15 kueri domain spesifik). Seluruh pipeline pengujian offline berhasil disiapkan menggunakan `pytest` dengan mock fixtures tanpa ketergantungan pada koneksi Ollama eksternal. Evaluasi baseline berhasil menangkap secara kuantitatif anomali utama sistem: 6 dari 35 kueri terpicu oleh *false refusal direct bypass*, dan 8 dari 35 kueri menampilkan gambar fasilitas secara keliru/jatuh ke fallback acak.

### 2. Daftar File Diubah / Dibuat
- **Branch Git:** `improve/rag-v2`
- **Backup Direktori:** `chroma_db_backup_20260919/` (612 chunk cadangan utuh)
- **File Konfigurasi & Lingkungan:**
  - `.gitignore`: ditambahkan pola `chroma_db_backup_*/` dan file temporer
  - `pytest.ini`: isolasi direktori testing (`testpaths = tests`, `norecursedirs = debug eval data chroma_db chroma_db_backup_*`)
- **Struktur Tes Offline:**
  - `tests/__init__.py`: inisialisasi package testing
  - `tests/conftest.py`: fixture mock Ollama API (`mock_ollama_chat`) dan fixture chunk jadwal valid (`sample_schedule_chunk`)
  - `tests/test_basic.py`: 4 unit test dasar (deteksi jadwal, sanitasi teks, ekstraksi prodi, mock LLM) — Status: 4 PASSED
- **Dataset & Runner Baseline:**
  - `eval/baseline/baseline_questions.csv`: 35 pertanyaan baseline (15 ground truth, 5 audit quick test, 15 custom queries)
  - `eval/baseline/run_baseline.py`: script eksekusi evaluasi baseline end-to-end
  - `eval/baseline/baseline_results.csv`: hasil tabular baseline (latensi, chunk, skor rerank, status bypass, gambar)
  - `eval/baseline/baseline_results.json`: log lengkap respons dan metadata chunk per kueri
- **Dokumentasi Log:**
  - `IMPROVEMENT_LOG.md`: dokumen log perbaikan ini

### 3. Hasil Pengujian & Evaluasi Baseline

#### Ringkasan Metrik Kuantitatif Baseline (35 Kueri)
| Metrik | Nilai Baseline (Fase 0) | Catatan / Target Fase Berikutnya |
| :--- | :--- | :--- |
| **Total Kueri Uji** | 35 kueri | 15 GT + 5 Audit + 15 Domain Tambahan |
| **Direct Bypass Terpicu** | **6 / 35 (17.1%)** | **Semua 6 kueri menghasilkan false refusal** |
| **Kueri dengan Gambar Fasilitas** | **8 / 35 (22.9%)** | Termasuk fallback salah pada penolakan denah |
| **Rerata Latensi Total** | 3.94 detik | Kombinasi retrieval dense + rerank + LLM cloud |
| **Rerata Latensi Retrieval** | 0.86 detik | Reranking MiniLM-L-6-v2 + ChromaDB |
| **Rerata Latensi LLM** | 3.08 detik | `gemma4:31b-cloud` via Ollama API |
| **Offline Pytest Pass Rate** | **4 / 4 (100%)** | Smoke tests berjalan tanpa Ollama / GPU |

#### Rincian Kueri Terdampak Bug Kritis pada Baseline
1. **Kueri 1 ("Di mana lokasi kampus Pradita University?")**:
   - *Status:* False Refusal via Bypass Dosen.
   - *Jawaban Sistem:* "Saya belum menemukan entri jadwal yang secara eksplisit menuliskan **mana lokasi kampus Pradita University** pada chunk yang berhasil diambil. Jadi saya tidak akan menebak mata kuliahnya."
   - *Penyebab:* Frasa "mana lokasi kampus Pradita University" diklasifikasikan sebagai nama dosen.
2. **Kueri 14 ("Apa saja mata kuliah yang diajarkan oleh [ANON] di program Informatika?")**:
   - *Status:* False Refusal via Bypass Dosen.
   - *Jawaban Sistem:* "Saya belum menemukan entri jadwal yang secara eksplisit menuliskan **diajarkan oleh [ANON] program**..."
3. **Kueri 16 ("Siapa dosen pengampu Interaksi Manusia dan Komputer?")**:
   - *Status:* False Refusal via Bypass Dosen (Temuan Audit Utama).
   - *Jawaban Sistem:* "Saya belum menemukan entri jadwal yang secara eksplisit menuliskan **pengampu Interaksi Manusia Komputer** pada chunk yang berhasil diambil. Jadi saya tidak akan menebak mata kuliahnya."
   - *Fakta Konteks:* Chunk #1 (`1. TI - Jadwal Perkuliahan Genap 2025-2.rev.pdf`) memuat dosen pengampu tertulis `[ANON]`.
4. **Kueri 19 ("Apakah ada denah kampus atau peta lantai?")**:
   - *Status:* LLM menjawab penolakan ("Maaf sobat, saya tidak memiliki informasi tersebut"), namun UI tetap melampirkan 4 gambar acak (Auditorium, Front Office, Alloggio, Sport Court) karena fallback 1 gambar per kategori di `app.py:99-112`.
5. **Kueri 23, 24, 33**:
   - Semuanya salah terperangkap ke regex nama dosen `app.py:_extract_lecturer_query_name` dan memotong pemanggilan RAG/LLM dengan penolakan palsu.

### 4. Status Verifikasi Temuan Audit (0.3 a, b, c, d)
| Item Verifikasi | Status | Hasil Pembuktian Teknis |
| :--- | :--- | :--- |
| **0.3(a) Efektivitas `num_ctx` & `/v1` API** | **TERBUKTI** | Parameter konteks arsitektur `gemma4:31b-cloud` adalah 262.144 token; lokal `gemma2:2b` adalah 8.192 token (runner default Ollama adalah 2.048). Endpoint OpenAI-compatible `/v1/chat/completions` **TIDAK menghormati parameter num_ctx** yang dikirimkan via JSON payload/options (diabaikan oleh handler). Kontrol eksplisit wajib menggunakan native `/api/chat` dengan dictionary `options: {"num_ctx": ...}` atau konfigurasi Modelfile. |
| **0.3(b) Privasi `gemma4:31b-cloud`** | **TERBUKTI** | Pemeriksaan `/api/show` membuktikan parameter `remote_host: "https://ollama.com:443"`. Seluruh prompt dan data konteks yang dikirim ke `gemma4:31b-cloud` keluar dari mesin lokal dan diproses oleh Ollama Cloud, sehingga memiliki implikasi privasi data institusi kampus. |
| **0.3(c) Ketiadaan Layer Teks pada PDF** | **TIDAK TERBUKTI (Bukan Masalah)** | Seluruh 13 file PDF jadwal di `data/jadwal/` memiliki text layer digital lengkap (berkisar antara 3.159 s.d. 7.893 karakter per dokumen). Tidak ada satupun PDF yang merupakan scan raster. Ekstraksi digital murni adalah jalur yang tepat tanpa memerlukan OCR berbasis gambar yang berat. |
| **0.3(d) Dukungan PyMuPDF `find_tables()`** | **TERBUKTI** | Versi PyMuPDF terpasang adalah `1.27.2.3`. Method `page.find_tables()` didukung secara penuh (`hasattr(page, 'find_tables') == True`) dan berhasil mendeteksi grid sel pada halaman jadwal perkuliahan. |

### 5. Risiko, Hal Belum Selesai, dan Asumsi Default [DEFAULT]
- **Risiko Teridentifikasi:**
  - NumPy 2.5.2 di Python 3.12 lokal mengalami bentrok dengan library C-extension opsional pandas (`bottleneck` dan `numexpr`). Diatasi secara bersih pada modul dengan mengeset `sys.modules['bottleneck'] = None` dan `sys.modules['numexpr'] = None` sebelum modul data dimuat.
- **Hal yang Belum Selesai:**
  - Memasuki FASE 1: Perbaikan bug kritis (indeks entitas metadata untuk eliminasi false refusal pada bypass dosen, perbaikan path `ocr_jadwal.py`, kalkulasi anggaran context token dengan pemotongan per chunk utuh, dan pembetulan page number di `loader.py:147`).
- **Asumsi Default yang Digunakan [DEFAULT]:**
  - `[DEFAULT]` Bahasa respons sistem adalah Bahasa Indonesia (`RESPONSE_LANGUAGE = "id"`).
  - `[DEFAULT]` Menggunakan data lokal `data/web/*.txt` tanpa web scraping live.
  - `[DEFAULT]` File jadwal bertanda `.rev` secara mutlak menggantikan file non-rev untuk program studi yang sama.
  - `[DEFAULT]` Peta/denah kampus dinyatakan tidak tersedia; sistem tidak boleh menampilkan gambar fallback jika entitas denah tidak ditemukan.

---

## FASE 1 — Bug Kritis

### 1. Ringkasan yang Dikerjakan
Fase 1 telah menyelesaikan perbaikan seluruh bug kritis operasional sistem: (1.1) Membangun modul `rag/entity_index.py` untuk mengindeks entitas mata kuliah, nama dosen, kode MK, dan ruang dari metadata, serta merefaktor jalur bypass di `app.py` agar secara ketat hanya menghasilkan jawaban terstruktur positif (zero false refusal); (1.2) Memperbaiki bug path ganda pada `data/jadwal/ocr_jadwal.py` serta menambahkan parameter CLI `--input` dan `--output`; (1.3) Mengimplementasikan kontrol anggaran token konteks (`MAX_CONTEXT_TOKENS = 2500`, estimator konservatif, pemotongan per-chunk utuh) pada `rag/retriever.py`, pembatasan token riwayat, dan dukungan native endpoint Ollama `/api/chat` dengan parameter `options.num_ctx` eksplisit di `llm/ollama_client.py`; (1.4) Memperbaiki parser `rag/loader.py` untuk mengekstrak penanda halaman `--- Page N ---` sehingga dokumen PDF jadwal multi-halaman terindeks dengan nomor halaman yang benar (1 dan 2).

### 2. Daftar File Diubah / Dibuat
- **File Baru:**
  - `rag/entity_index.py`: modul pembuat indeks entitas (courses, lecturers, codes, rooms) dan resolver kueri langsung positif.
  - `tests/test_phase1.py`: test suite verifikasi Fase 1 (normalisasi, pencocokan entitas, anti-false refusal, pemotongan anggaran token utuh, parser halaman OCR).
- **File Dimodifikasi:**
  - `config.py`: penambahan konstanta `DEFAULT_NUM_CTX = 4096`, `MAX_CONTEXT_TOKENS = 2500`, `CONTEXT_MARGIN_TOKENS = 256`, `MAX_HISTORY_TURNS = 6`, `MAX_HISTORY_TOKENS = 500`, fungsi `estimate_tokens`, dan `OLLAMA_CHAT_API_URL`.
  - `app.py`: integrasi `_build_direct_schedule_answer` menggunakan `EntityIndex`, eliminasi total logika regex lama yang memicu false refusal.
  - `data/jadwal/ocr_jadwal.py`: perbaikan resolusi direktori input/output dan penambahan opsi CLI `--input` & `--output`.
  - `rag/__init__.py`: penambahan isolasi modul NumPy 2.x `bottleneck`/`numexpr` untuk kompatibilitas lingkungan eksekusi lokal.
  - `rag/loader.py`: parser regex `(?m)^---\s*Page\s+(\d+)\s*---` untuk pemisahan halaman dokumen jadwal multi-halaman.
  - `rag/retriever.py`: integrasi batas token anggaran `max_context_tokens` pada `_build_structured_context` dengan pemotongan per-chunk utuh dan pencatatan log omisi.
  - `llm/ollama_client.py`: implementasi pemanggilan native `/api/chat` dengan opsi `num_ctx`, `temperature`, `num_predict`, serta pemangkasan token riwayat percakapan.

### 3. Hasil Pengujian & Evaluasi Sebelum vs Sesudah

#### Tabel Perbandingan Sebelum vs Sesudah Fase 1
| Skenario Kueri / Kasus Uji | Perilaku Sebelum (Baseline Fase 0) | Perilaku Sesudah (Fase 1) | Status |
| :--- | :--- | :--- | :--- |
| **Audit Q1**: *"Siapa dosen pengampu Interaksi Manusia dan Komputer?"* | **False Refusal:** "Saya belum menemukan entri jadwal yang secara eksplisit menuliskan pengampu Interaksi Manusia Komputer..." | **Jawaban Positif:** Tabel terstruktur resmi: Theresia Herlina, S.Kom., M.T (Informatika, Smt II, Kelas A+B, Senin 08.25-11.05, Ruang A306). | **TERSELESAIKAN** |
| **Variasi Q1a**: *"dosen matkul Interaksi Manusia dan Komputer"* | False Refusal via regex bypass | Jawaban Positif terstruktur seketika (<10ms via entity index) | **TERSELESAIKAN** |
| **Variasi Q1b**: *"Interaksi Manusia dan Komputer diajar siapa"* | False Refusal via regex bypass | Jawaban Positif terstruktur seketika (<10ms via entity index) | **TERSELESAIKAN** |
| **Kueri 1**: *"Di mana lokasi kampus Pradita University?"* | **False Refusal:** "Saya belum menemukan entri jadwal... mana lokasi kampus..." | **Bypass = None:** Kueri diteruskan ke RAG & LLM secara bersih tanpa intervensi penolakan palsu. | **TERSELESAIKAN** |
| **Kueri 14**: *"Apa saja mata kuliah yang diajarkan oleh Theresia Herlina di program Informatika?"* | **False Refusal:** "Saya belum menemukan... diajarkan oleh Theresia Herlina program..." | **Jawaban Positif:** Tabel lengkap 5 jadwal mata kuliah resmi Theresia Herlina. | **TERSELESAIKAN** |
| **Multi-page OCR Loading**: `data/jadwal_ocr/*.txt` | Semua dokumen jadwal ditandai `page = 1` | Dokumen multi-halaman terurai menjadi halaman 1 dan 2 secara mandiri. | **TERSELESAIKAN** |
| **Konflik num_ctx & Truncation** | Prompt dapat terpotong di tengah baris teks jika konteks besar; num_ctx diabaikan `/v1`. | Konteks dipotong per chunk utuh (`MAX_CONTEXT_TOKENS`); `options.num_ctx` dikirim ke `/api/chat`. | **TERSELESAIKAN** |
| **Total Pytest Suite** | 4 passed | **10 passed, 0 failed (100%)** | **PASSED** |

### 4. Status Temuan Audit Terkait Fase 1
- **[KRITIS] app.py regex nama dosen salah dan bypass LLM dengan penolakan palsu:** **TERBUKTI & SUDAH DIPERBAIKI**. Jalur bypass kini menggunakan indeks entitas eksklusif yang hanya merespons jika terdapat entitas mata kuliah atau dosen resmi; dan hanya memancarkan respons positif. Jika kueri tidak cocok, sistem mengembalikan `None` dan meneruskan ke pipeline RAG/LLM.
- **[KRITIS] Tidak ada batas token konteks (rag/retriever.py:502-548):** **TERBUKTI & SUDAH DIPERBAIKI**. `_build_structured_context` kini mengestimasi token per chunk dan menghentikan inklusi chunk saat batas 2500 token tercapai tanpa memotong baris jadwal.
- **[TINGGI] Path ganda data/jadwal/data/jadwal pada ocr_jadwal.py:** **TERBUKTI & SUDAH DIPERBAIKI**. Direktori input dan output kini menggunakan path absolut berbasis `PROJECT_ROOT` dan dapat dikonfigurasi via CLI `--input` dan `--output`.
- **[SEDANG] loader.py:147 page selalu bernilai 1:** **TERBUKTI & SUDAH DIPERBAIKI**. Parser membaca penanda `--- Page N ---` dan memecah dokumen OCR menjadi unit per halaman dengan nomor halaman akurat.

### 5. Risiko, Hal Belum Selesai, dan Asumsi Default [DEFAULT]
- **Hal yang Belum Selesai:**
  - Melangkah ke FASE 2: Keamanan prompt injection, pemisahan role system vs data berbatas acak (`<konteks_{B}>`), modul `rag/sanitize.py`, pembatasan input user (500 karakter) & rate limit, modul `rag/output_guard.py`, serta dataset uji injeksi `tests/test_injection.py` dan `eval/injection_cases.csv`.
- **Asumsi Default yang Digunakan [DEFAULT]:**
  - `[DEFAULT]` Jalur bypass hanya beroperasi pada entitas jadwal terstruktur; kueri fasilitas atau pertanyaan umum sepenuhnya ditangani oleh RAG + LLM.

---
