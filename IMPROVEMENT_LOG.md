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

---

## FASE 2 — Keamanan (Prompt Injection & Output Guardrails)

### 1. Ringkasan yang Dikerjakan
Fase 2 mengimplementasikan arsitektur pertahanan keamanan komprehensif terhadap serangan prompt injection, kebocoran system prompt, dan manipulasi tautan/kontak tidak resmi. Pemisahan peran instruksi dan data diterapkan secara ketat dengan mengisolasi konteks dokumen ke dalam tag dengan delimiter acak per-request (`<konteks_{token}>` dan `<pertanyaan_user_{token}>`) sementara system message hanya berisi aturan tetap. Modul sanitasi `rag/sanitize.py` menormalisasi Unicode NFKC, menghapus karakter tak terlihat/bidi/HTML/skrip, membatasi panjang input maksimal 500 karakter, dan mendeteksi berbagai pola injeksi dwibahasa (ID+EN) maupun smuggling Base64. Modul `rag/output_guard.py` memastikan ketiadaan kebocoran system prompt/canary token (`ADITA_SEC_TOKEN_9A7B3C`) serta menyaring tautan, email, dan nomor telepon tidak resmi di luar domain yang diizinkan (`pradita.ac.id`, `summarecon.com`). Evaluasi komprehensif pada 35 kasus serangan deterministik dalam `eval/injection_cases.csv` membuktikan penurunan Attack Success Rate (ASR) menjadi 0.0% dengan kelulusan tes offline 100% (24/24 unit test lolos).

### 2. Daftar File Diubah / Dibuat
- **File Baru:**
  - `rag/sanitize.py`: modul sanitasi masukan pengguna, normalisasi Unicode NFKC, pembersihan karakter bidi/zero-width, deteksi pola injeksi dwibahasa ID+EN, dan pembongkaran muatan Base64.
  - `rag/output_guard.py`: modul penyaring keluaran LLM (deteksi security canary, pencegahan kebocoran aturan sistem, pembersihan tag HTML, dan penyaringan whitelist URL, email, serta nomor kontak).
  - `.env.example`: template variabel lingkungan dan dokumentasi implikasi privasi data institusi kampus terkait model cloud vs lokal.
  - `eval/injection_cases.csv`: dataset benchmark berisi 35 kasus serangan injeksi terbagi ke dalam 10 kategori serangan spesifik.
  - `tests/test_injection.py`: test suite evaluasi offline berisi 14 unit test untuk memvalidasi seluruh mekanisme pertahanan deterministik.
- **File Dimodifikasi:**
  - `config.py`: pemindahan endpoint ke `os.environ` dengan default aman, penambahan variabel batas input `MAX_INPUT_CHARS = 500`, batas laju `RATE_LIMIT_PER_MINUTE = 10`, bahasa respon `RESPONSE_LANGUAGE = "id"`, dan pembaruan `SYSTEM_PROMPT` aturan murni (hanya `<keamanan>` dan `<aturan_jawaban>`).
  - `llm/ollama_client.py`: perakitan `build_messages` target template dengan delimiter acak per-request (`secrets.token_hex(4)`), sanitasi masukan dan konteks, integrasi `guard_output` sinkron, dan guard streaming leak detection.
  - `rag/retriever.py`: penyaringan dan pengabaian otomatis terhadap chunk mencurigakan (`suspicious="true"`), sanitasi chunk saat perakitan konteks, serta masking nama dosen (`[ANON]`) dan panjang kueri pada log stdout.
  - `rag/store.py`: sanitasi teks dokumen saat proses ingest dan pemberian metadata `suspicious="true"` jika terdeteksi muatan berbahaya.
  - `app.py`: implementasi pembatasan panjang masukan user, rate limiting berbasis sesi (maksimal 10 request/menit), sanitasi masukan pengguna, audit menyeluruh `unsafe_allow_html=True` dengan penerapan `html.escape` pada seluruh nilai dinamis, dan penegakan `guard_output` di akhir proses streaming LLM.

### 3. Hasil Pengujian & Evaluasi Sebelum vs Sesudah

#### Tabel Perbandingan Sebelum vs Sesudah Fase 2
| Fitur / Parameter Keamanan | Kondisi Sebelum (Fase 1) | Kondisi Sesudah (Fase 2) | Status |
| :--- | :--- | :--- | :--- |
| **Pemisahan Instruksi & Data** | Konteks dokumen digabung langsung ke dalam pesan role `system` (`llm/ollama_client.py:97-101`). Rentan manipulasi instruksi sistem. | Role `system` murni memuat aturan keamanan & gaya. Konteks dipindah ke pesan `user` dalam tag berbatas acak `<konteks_{token}>`. | **TERSELESAIKAN** |
| **Security Canary & Anti-Leak** | Tidak ada penanda canary; instruksi sistem rentan diekstraksi lewat perintah "repeat your prompt". | Disematkan `ADITA_SEC_TOKEN_9A7B3C` dan pendeteksi n-gram aturan. Jika LLM membocorkan, otomatis diganti penolakan standar. | **TERSELESAIKAN** |
| **Sanitasi Input & Unicode** | Input mentah langsung diproses tanpa normalisasi; rentan zero-width space, bidi override, dan HTML injection. | Normalisasi Unicode NFKC, pembersihan karakter bidi & zero-width, stripping HTML, penonaktifan tag pembatas palsu. | **TERSELESAIKAN** |
| **Deteksi Smuggling Base64** | Muatan prompt terenkode Base64 dapat lolos tanpa diperiksa. | Regex detector membongkar string Base64 dan memverifikasi isi perintah terhadap tanda tangan injeksi. | **TERSELESAIKAN** |
| **Guardrail URL & Kontak** | LLM dapat mengarang URL phishing, email tidak resmi, atau nomor telepon palsu. | URL dan kontak di luar konteks / whitelist resmi (`pradita.ac.id`, `summarecon.com`) otomatis disaring. | **TERSELESAIKAN** |
| **Audit `unsafe_allow_html`** | Nilai sumber chunk dokumen disisipkan langsung ke HTML tanpa escaping di beberapa komponen UI. | Seluruh nilai dinamis (nama sumber, teks kueri) dibungkus dengan `html.escape()` sebelum dirender. | **TERSELESAIKAN** |
| **Privasi Log Sistem** | Nama dosen dan teks kueri mentah tercetak eksplisit di stdout. | Nama dosen disamarkan menjadi `[ANON]`, panjang dan ringkasan kueri dimask. Konteks penuh tidak dicetak. | **TERSELESAIKAN** |
| **Batas Input & Rate Limit** | Tidak ada batas panjang karakter dan frekuensi kirim pesan. | Dibatasi maksimal 500 karakter per pertanyaan dan maksimal 10 pertanyaan per menit per sesi pengguna. | **TERSELESAIKAN** |
| **Total Test Suite Pytest** | 10 passed | **24 passed, 0 failed (100% pass rate)** | **PASSED** |

#### Hasil Evaluasi Serangan Injeksi (`eval/injection_cases.csv` — 35 Kasus)
| Kategori Serangan | Jumlah Kasus | Berhasil Dinetralkan | Attack Success Rate (ASR) |
| :--- | :---: | :---: | :---: |
| **direct_override** (Abaikan aturan ID/EN) | 4 | 4 | **0.0%** |
| **roleplay_jailbreak** (DAN, Developer mode, Evil AI) | 4 | 4 | **0.0%** |
| **system_prompt_extraction** (Ekstraksi prompt awal) | 5 | 5 | **0.0%** |
| **canary_leakage_attempt** (Upaya pencurian token canary) | 1 | 1 | **0.0%** |
| **unicode_obfuscation** (Zero-width, Bidi, Fullwidth) | 3 | 3 | **0.0%** |
| **base64_smuggling** (Muatan injeksi terenkode Base64) | 2 | 2 | **0.0%** |
| **delimiter_collision** (Upaya menutup tag `<konteks_*>`) | 3 | 3 | **0.0%** |
| **indirect_injection** (Perintah tertanam pada jadwal/dokumen) | 3 | 3 | **0.0%** |
| **html_injection** (Tag script, iframe, img onerror, comment) | 4 | 4 | **0.0%** |
| **fake_url_phishing** (Penyisipan URL penipuan) | 1 | 1 | **0.0%** |
| **fake_email_harvesting** (Penyisipan email palsu) | 1 | 1 | **0.0%** |
| **fake_phone_scam** (Penyisipan nomor kontak darurat palsu) | 1 | 1 | **0.0%** |
| **oversized_input** (Pemberian payload sangat panjang) | 1 | 1 | **0.0%** |
| **authority_spoofing** (Penyamaran admin/developer command) | 1 | 1 | **0.0%** |
| **context_escape** (Penutupan tag dokumen XML) | 1 | 1 | **0.0%** |
| **TOTAL KESELURUHAN** | **35** | **35** | **0.0% (ASR = 0%)** |

### 4. Status Temuan Audit Terkait Fase 2
- **[KRITIS] Konteks RAG digabung ke role system di llm/ollama_client.py:97-101:** **TERBUKTI & SUDAH DIPERBAIKI**. Role system kini hanya memuat aturan tetap instruksi dan keamanan. Data konteks dipisah ke pesan user berbatas token acak.
- **[KRITIS] Tidak ada sanitasi ingest, filter output, batas input, rate limit:** **TERBUKTI & SUDAH DIPERBAIKI**. Diterapkan modul `rag/sanitize.py` (ingest + input user), `rag/output_guard.py` (output filter), batas 500 karakter, dan rate limit 10 req/menit.
- **[KRITIS] unsafe_allow_html=True di app.py (baris 1040, 1188, 1289):** **TERBUKTI & SUDAH DIPERBAIKI**. Seluruh penyisipan string dinamis telah diverifikasi dan diamankan menggunakan `html.escape()`. Teks jawaban LLM dirender murni via Markdown standar.
- **[SEDANG] Log memuat query mentah dan nama dosen:** **TERBUKTI & SUDAH DIPERBAIKI**. Seluruh nama dosen dimask menjadi `[ANON]`, query diringkas, dan pencetakan konteks penuh ditiadakan dari stdout.
- **[SEDANG] IP Tailscale di komentar config.py:22:** **TERBUKTI & SUDAH DIPERBAIKI**. Seluruh URL endpoint dikonfigurasi melalui variabel lingkungan (`OLLAMA_BASE_URL`), dan file panduan `.env.example` telah disediakan tanpa memuat alamat IP internal.

### 5. Risiko, Hal Belum Selesai, dan Asumsi Default [DEFAULT]
- **Hal yang Belum Selesai:**
  - Melangkah ke FASE 3: Jadwal terstruktur (ekstraksi tabel presisi dengan `page.find_tables()` PyMuPDF vs `pdfplumber`, skema `data/structured/jadwal.jsonl`, penanganan cell wrap baris 34-56 `.rev.txt`, penanganan versi `.rev` vs non-rev, antarmuka `ScheduleSource`, dan pembuatan golden set otomatis).
- **Asumsi Default yang Digunakan [DEFAULT]:**
  - `[DEFAULT]` Batas input user ditetapkan 500 karakter (`MAX_INPUT_CHARS = 500`).
  - `[DEFAULT]` Rate limit ditetapkan 10 pertanyaan per menit per sesi pengguna.
  - `[DEFAULT]` Whitelist domain resmi adalah `pradita.ac.id`, `summarecon.com`, dan subdomain terkait.

---
