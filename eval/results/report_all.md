# Laporan Evaluasi RAG Multi-Model (Paper Aligned)
**Tanggal:** 31 May 2026, 22:44
**Penilaian Human Review:** Tergabung untuk semua model
**Model yang dievaluasi:** `gemma2:2b`, `qwen3:1.7B`, `llama3.2:1b`
**Jumlah pertanyaan:** 15

---

## Ringkasan Performa (Rata-rata Semua Pertanyaan)

| Model | SemSim | Gemini Judge | Claude Judge | Human Review | Latency (s) | Throughput (tok/s) |
|-------|--------|--------------|--------------|------|-------------|--------------------|
| `gemma2:2b` | 0.9164 | 93.0 | 91.3 | 90.1 | 8.30 | 13.3 |
| `qwen3:1.7B` | 0.9112 | 91.7 | 89.7 | 90.7 | 25.55 | 20.8 |
| `llama3.2:1b` | 0.8319 | 79.3 | 76.3 | 77.9 | 12.23 | 26.0 |

> [!NOTE]
> **Model terbaik (Gemini Judge):** `qwen3:1.7B` (89.7/100)
> **Model terbaik (Claude Judge):** `qwen3:1.7B` (87.0/100)
> **Model tercepat:** `llama3.2:1b` (26.0 tok/s)

---

## Detail Per Pertanyaan

### Q01 — Informasi Kampus [Sederhana]

**Pertanyaan:** Di mana lokasi kampus Pradita University?

**Referensi jawaban:**
> Pradita University memiliki dua kampus. Kampus utama (Gading Serpong) berlokasi di Scientia Business Park, Tower 1, Jalan Raya Boulevard Blok O/1, Summarecon Serpong, Kabupaten Tangerang, Banten 15810. Kampus Jakarta berlokasi di Menara Satu Building, Jl. Boulevard Raya LA 3 No.1, Sentra Kelapa Gadi...

**Hasil per model:**

| Model | SemSim | Gemini | Claude | Human Review | Latency | Tok/s |
|-------|--------|--------|--------|--------------|---------|-------|
| `gemma2:2b` | 0.9709 | 100.0 | 100.0 | 100 | 15.41s | 13.8 |
| `qwen3:1.7B` | 0.9580 | 100.0 | 100.0 | 100 | 24.72s | 19.9 |
| `llama3.2:1b` | 0.8783 | 80.0 | 75.0 | 78 | 23.88s | 21.9 |

**Jawaban model & Evaluasi LLM Judge (Gemini 3.1 Pro & Claude Sonnet 4.6):**

- **`gemma2:2b`:** Kampus Pradita University ada di dua lokasi: Jakarta Campus dan Gading Serpong Campus (Kampus Utama).  * **Jakarta Campus:** Menara Satu Building, Jl. Boulevard Raya LA 3 No.1, Sentra Kelapa Gading, Jakarta Utara, DKI Jakarta 14240 * **Gading Serpong...
  * **Gemini 3.1 Pro:** Sangat lengkap dan akurat menyebutkan kedua kampus beserta alamat.
  * **Claude Sonnet 4.6:** Akurat 100%: menyebutkan kedua alamat kampus beserta nama gedung dan kode pos.
  * **Human Reviewer:** Sangat lengkap dan akurat menyebutkan kedua kampus beserta alamat. (Catatan Tambahan: Akurat 100%: menyebutkan kedua alamat kampus beserta nama gedung dan kode pos.) (Skor: 100/100)

- **`qwen3:1.7B`:** Lokasi kampus Pradita University terdiri dari dua kampus:   1. **Kampus Utama** di **Gading Serpong, Summarecon Serpong, Tangerang, Banten** (alamat: Jl. Boulevard Gading Serpong Blok 0/1, Scientia Business Park, Tower 1).   2. **Kampus Jakarta** di ...
  * **Gemini 3.1 Pro:** Model berhasil menjawab kali ini dengan akurasi sangat tinggi ditambah link peta.
  * **Claude Sonnet 4.6:** Jawaban sangat rapi: dua kampus dengan bullet bersarang, alamat lengkap, ditambah link Google Maps.
  * **Human Reviewer:** Model berhasil menjawab kali ini dengan akurasi sangat tinggi ditambah link peta. (Catatan Tambahan: Jawaban sangat rapi: dua kampus dengan bullet bersarang, alamat lengkap, ditambah link Google Maps.) (Skor: 100/100)

- **`llama3.2:1b`:** Lokasi kampus Pradita University terletak di Jakarta dan Gading Serpong, Banten.  Dokumen #1 menunjukkan bahwa lingkungan sekitar kampus harus nyaman dan fasilitasnya dapat menunjang kegiatan mahasiswa.  Dokumen #2 menjelaskan prosedur pendaftaran (H...
  * **Gemini 3.1 Pro:** Cukup akurat, merangkum lokasi kampus di Jakarta dan Gading Serpong dengan baik.
  * **Claude Sonnet 4.6:** Jawaban mencakup lokasi Jakarta dan Gading Serpong dengan benar, namun kurang detail alamat spesifik dari referensi.
  * **Human Reviewer:** Cukup akurat, merangkum lokasi kampus di Jakarta dan Gading Serpong dengan baik. (Catatan Tambahan: Jawaban mencakup lokasi Jakarta dan Gading Serpong dengan benar, namun kurang detail alamat spesifik dari referensi.) (Skor: 78/100)


---

### Q02 — Informasi Akademik [Sederhana]

**Pertanyaan:** Apa saja program studi yang tersedia di Pradita University?

**Referensi jawaban:**
> Pradita University menawarkan berbagai program studi, antara lain: Teknik Informatika, Sistem Informasi, Pariwisata, Perencanaan Wilayah dan Kota, Arsitektur, Teknik Sipil, Desain Komunikasi Visual, Desain Interior, Seni Kuliner, Manajemen Bisnis, Akuntansi, dan Food & Beverage.

**Hasil per model:**

| Model | SemSim | Gemini | Claude | Human Review | Latency | Tok/s |
|-------|--------|--------|--------|--------------|---------|-------|
| `gemma2:2b` | 0.9187 | 95.0 | 85.0 | 90 | 16.32s | 12.4 |
| `qwen3:1.7B` | 0.9338 | 90.0 | 95.0 | 92 | 33.72s | 19.8 |
| `llama3.2:1b` | 0.8428 | 85.0 | 80.0 | 82 | 5.70s | 25.0 |

**Jawaban model & Evaluasi LLM Judge (Gemini 3.1 Pro & Claude Sonnet 4.6):**

- **`gemma2:2b`:** Berikut adalah daftar program studi yang tersedia di Pradita University:  **JENJANG SARJANA (S1) - BACHELOR'S DEGREE:**  * Architecture (Arsitektur) * Urban Planning (Perencanaan Kota) * Civil Engineering (Teknik Sipil) * Interior Design (Desain Inte...
  * **Gemini 3.1 Pro:** Hampir mencakup semua jurusan, terstruktur rapi per jenjang.
  * **Claude Sonnet 4.6:** Hanya 6 prodi S1, melewatkan Informatika, Sistem Informasi, Pariwisata, Manajemen, F&B. Struktur bagus tapi tidak lengkap.
  * **Human Reviewer:** Hampir mencakup semua jurusan, terstruktur rapi per jenjang. (Catatan Tambahan: Hanya 6 prodi S1, melewatkan Informatika, Sistem Informasi, Pariwisata, Manajemen, F&B. Struktur bagus tapi tidak lengkap.) (Skor: 90/100)

- **`qwen3:1.7B`:** Berikut daftar program studi di Pradita University:  ### **Jenjang Sarjana (S1)** 1. Arsitektur   2. Perencanaan Kota   3. Teknik Sipil   4. Desain Interior   5. Desain Komunikasi Visual (DKV)   6. Akuntansi    ### **Jenjang Diploma (D3)** 1. Seni Ku...
  * **Gemini 3.1 Pro:** Lengkap namun format markdown tabel sedikit patah.
  * **Claude Sonnet 4.6:** 10 prodi S1 plus D3 dan S2 — paling lengkap. Sedikit perbedaan nama (Manajemen vs Manajemen Bisnis). Catatan dokumen sedikit mengganggu.
  * **Human Reviewer:** Lengkap namun format markdown tabel sedikit patah. (Catatan Tambahan: 10 prodi S1 plus D3 dan S2 — paling lengkap. Sedikit perbedaan nama (Manajemen vs Manajemen Bisnis). Catatan dokumen sedikit mengganggu.) (Skor: 92/100)

- **`llama3.2:1b`:** Berikut adalah jawaban terpadu dari pertanyaan yang diajukan:  Dokumen #1: Program Studi S1 Architecture (Arsitektur) Dokumen #2: Program Studi Bussiness Management Dokumen #3: Program Studi Culinary Arts (Seni Kuliner) Dokumen #4: Program Studi Info...
  * **Gemini 3.1 Pro:** Mencakup jurusan tapi format agak mekanis (mengutip 'Dokumen #1' dll).
  * **Claude Sonnet 4.6:** Membaca isi dokumen mentah untuk mendaftar prodi, tetapi agak terputus. Mencakup S1 Architecture dll.
  * **Human Reviewer:** Mencakup jurusan tapi format agak mekanis (mengutip 'Dokumen #1' dll). (Catatan Tambahan: Membaca isi dokumen mentah untuk mendaftar prodi, tetapi agak terputus. Mencakup S1 Architecture dll.) (Skor: 82/100)


---

### Q03 — Penerimaan Mahasiswa [Sederhana]

**Pertanyaan:** Bagaimana cara mendaftar masuk ke Pradita University?

**Referensi jawaban:**
> Untuk mendaftar ke Pradita University, calon mahasiswa dapat mengunjungi website resmi pradita.ac.id atau menghubungi pihak kampus melalui email info@pradita.ac.id. Pendaftaran dilakukan secara online melalui portal penerimaan mahasiswa baru.

**Hasil per model:**

| Model | SemSim | Gemini | Claude | Human Review | Latency | Tok/s |
|-------|--------|--------|--------|--------------|---------|-------|
| `gemma2:2b` | 0.9426 | 100.0 | 100.0 | 100 | 5.37s | 12.4 |
| `qwen3:1.7B` | 0.9092 | 100.0 | 100.0 | 100 | 27.19s | 19.7 |
| `llama3.2:1b` | 0.8501 | 90.0 | 90.0 | 90 | 23.28s | 20.0 |

**Jawaban model & Evaluasi LLM Judge (Gemini 3.1 Pro & Claude Sonnet 4.6):**

- **`gemma2:2b`:** Untuk mendaftar masuk ke Pradita University, kamu bisa kunjungi website Pendaftaran: https://www.pradita.ac.id/admission/enrollment-information atau hubungi info@pradita.ac.id.
  * **Gemini 3.1 Pro:** Instruksi pendaftaran sangat detail, runut, dan dilengkapi URL.
  * **Claude Sonnet 4.6:** 7 langkah pendaftaran runut dan akurat, disertai link portal.
  * **Human Reviewer:** Instruksi pendaftaran sangat detail, runut, dan dilengkapi URL. (Catatan Tambahan: 7 langkah pendaftaran runut dan akurat, disertai link portal.) (Skor: 100/100)

- **`qwen3:1.7B`:** **Cara Mendaftar Masuk Pradita University:**   1. **Membeli dan mengisi Formulir Pendaftaran**   2. **Menyerahkan dokumen dan data ke bagian Admission**   3. **Mengikuti ujian saringan masuk (USM)**   4. **Mendapatkan Letter of Offering (LOO)**   5. ...
  * **Gemini 3.1 Pro:** Langkah pendaftaran lengkap dengan tautan.
  * **Claude Sonnet 4.6:** Langkah pendaftaran 1-6 (lebih ringkas dari gemma) disertai kontak dan link. Tepat.
  * **Human Reviewer:** Langkah pendaftaran lengkap dengan tautan. (Catatan Tambahan: Langkah pendaftaran 1-6 (lebih ringkas dari gemma) disertai kontak dan link. Tepat.) (Skor: 100/100)

- **`llama3.2:1b`:** Berikut jawaban pertanyaan yang diajukan berdasarkan konteks yang diberikan:  1. **Konteks Dokumen #1**: Proses pendaftaran Pradita University melalui prosedur enrollment. 2. Jawabannya: Informasi tersebut tidak ada di dokumen tersebut, sehingga jawa...
  * **Gemini 3.1 Pro:** Memberikan langkah-langkah pendaftaran yang cukup jelas berdasarkan konteks.
  * **Claude Sonnet 4.6:** Langkah-langkah pendaftaran disebutkan dengan baik walau agak terpenggal di awal.
  * **Human Reviewer:** Memberikan langkah-langkah pendaftaran yang cukup jelas berdasarkan konteks. (Catatan Tambahan: Langkah-langkah pendaftaran disebutkan dengan baik walau agak terpenggal di awal.) (Skor: 90/100)


---

### Q04 — Informasi Keuangan [Sederhana]

**Pertanyaan:** Berapa harga biaya kuliah per semester untuk program Information Technology & Business Information System di Pradita University?

**Referensi jawaban:**
> Biaya kuliah per semester untuk program Information Technology & Business Information System adalah Rp 7.500.000 (BPP), ditambah Rp 350.000 per SKS (untuk 20 SKS = Rp 7.000.000), dan Student Service Rp 750.000. Total keseluruhan per semester bisa mencapai sekitar Rp 15.250.000, belum termasuk uang p...

**Hasil per model:**

| Model | SemSim | Gemini | Claude | Human Review | Latency | Tok/s |
|-------|--------|--------|--------|--------------|---------|-------|
| `gemma2:2b` | 0.7991 | 40.0 | 35.0 | 38 | 2.63s | 12.1 |
| `qwen3:1.7B` | 0.8203 | 40.0 | 35.0 | 38 | 24.49s | 21.0 |
| `llama3.2:1b` | 0.7899 | 40.0 | 35.0 | 38 | 4.96s | 28.2 |

**Jawaban model & Evaluasi LLM Judge (Gemini 3.1 Pro & Claude Sonnet 4.6):**

- **`gemma2:2b`:** Rp 7.500.000,-
  * **Gemini 3.1 Pro:** Hanya menyebutkan BPP, tidak mencakup biaya SKS dan Student Service sehingga totalnya tidak akurat.
  * **Claude Sonnet 4.6:** Hanya BPP (Rp 7.5jt), mengabaikan biaya SKS (Rp 7jt) dan Student Service (Rp 750k). Total seharusnya ~Rp 15.25jt.
  * **Human Reviewer:** Hanya menyebutkan BPP, tidak mencakup biaya SKS dan Student Service sehingga totalnya tidak akurat. (Catatan Tambahan: Hanya BPP (Rp 7.5jt), mengabaikan biaya SKS (Rp 7jt) dan Student Service (Rp 750k). Total seharusnya ~Rp 15.25jt.) (Skor: 38/100)

- **`qwen3:1.7B`:** **Harga Biaya Kuliah Per Semester untuk Program Information Technology & Business Information System:**   Rp 7.500.000,- (BPP) + Rp 750.000,- (Student Service) = **Rp 8.250.000,-** per semester.    **Penjelasan:**   Dari dokumen #2, biaya per semeste...
  * **Gemini 3.1 Pro:** Hanya menangkap angka BPP pertama tanpa memperhitungkan biaya SKS.
  * **Claude Sonnet 4.6:** Menangkap BPP yang benar (Rp 7.5jt) tapi secara eksplisit menyatakan 'nilai biaya per semester sama dengan VCD' — perbandingan yang membingungkan dan tidak diminta.
  * **Human Reviewer:** Hanya menangkap angka BPP pertama tanpa memperhitungkan biaya SKS. (Catatan Tambahan: Menangkap BPP yang benar (Rp 7.5jt) tapi secara eksplisit menyatakan 'nilai biaya per semester sama dengan VCD' — perbandingan yang membingungkan dan tidak diminta.) (Skor: 38/100)

- **`llama3.2:1b`:** Harga biaya kuliah per semester untuk program Informasi Teknologi dan Sistem Informasi (ITS) di Pradita University adalah Rp 7.500.000,-.  Namun, perlu diingat bahwa informasi tersebut tidak ada dalam dokumen yang disebutkan. Oleh karena itu, jawaban...
  * **Gemini 3.1 Pro:** Hanya menyebutkan Rp 7.500.000,- yang merupakan BPP saja, tidak menghitung total SKS.
  * **Claude Sonnet 4.6:** Hanya menyebutkan Rp 7.500.000,- (BPP) tanpa menghitung total dengan SKS dan biaya layanan.
  * **Human Reviewer:** Hanya menyebutkan Rp 7.500.000,- yang merupakan BPP saja, tidak menghitung total SKS. (Catatan Tambahan: Hanya menyebutkan Rp 7.500.000,- (BPP) tanpa menghitung total dengan SKS dan biaya layanan.) (Skor: 38/100)


---

### Q05 — Fasilitas Kampus [Sederhana]

**Pertanyaan:** Apa saja fasilitas yang tersedia di kampus Pradita?

**Referensi jawaban:**
> Pradita University memiliki berbagai fasilitas lengkap, antara lain: auditorium, laboratorium komputer, studio desain, Front Office Practice Area (Hospitality & Tourism Lab), Student Boarding House District - Cluster Alloggio (asrama mahasiswa), Sport Court, ruang kelas modern, dan kawasan Summareco...

**Hasil per model:**

| Model | SemSim | Gemini | Claude | Human Review | Latency | Tok/s |
|-------|--------|--------|--------|--------------|---------|-------|
| `gemma2:2b` | 0.9196 | 100.0 | 100.0 | 100 | 12.64s | 13.0 |
| `qwen3:1.7B` | 0.9058 | 100.0 | 100.0 | 100 | 26.63s | 20.0 |
| `llama3.2:1b` | 0.9011 | 90.0 | 85.0 | 88 | 36.47s | 23.5 |

**Jawaban model & Evaluasi LLM Judge (Gemini 3.1 Pro & Claude Sonnet 4.6):**

- **`gemma2:2b`:** Fasilitas yang tersedia di kampus Pradita University antara lain:  * Ruang kelas dengan kapasitas 50-80 orang (fasilitas AC, LCD dan sound system) * Lab komputer * Studio green screen * Studio e-learning * Auditorium dengan kapasitas lebih dari 350 k...
  * **Gemini 3.1 Pro:** Tabel fasilitas komprehensif dan akurat.
  * **Claude Sonnet 4.6:** Fasilitas dikategorikan dengan sangat baik dan mencakup semua item kunci dari referensi.
  * **Human Reviewer:** Tabel fasilitas komprehensif dan akurat. (Catatan Tambahan: Fasilitas dikategorikan dengan sangat baik dan mencakup semua item kunci dari referensi.) (Skor: 100/100)

- **`qwen3:1.7B`:** Berikut adalah fasilitas yang tersedia di kampus Pradita University:  | Kategori Fasilitas | Contoh Fasilitas | |-------------------|------------------| | **Fasilitas Belajar** | Ruang kelas (AC, LCD, sound), lab komputer, studio green screen, studio...
  * **Gemini 3.1 Pro:** Kategorisasi fasilitas sangat rapi.
  * **Claude Sonnet 4.6:** Format tiga-bagian (Akademika, Transportasi, Lain-lain) paling terstruktur dari semua model. Termasuk workshop lab dan podcast room.
  * **Human Reviewer:** Kategorisasi fasilitas sangat rapi. (Catatan Tambahan: Format tiga-bagian (Akademika, Transportasi, Lain-lain) paling terstruktur dari semua model. Termasuk workshop lab dan podcast room.) (Skor: 100/100)

- **`llama3.2:1b`:** Dokumen #1: Gedung Kampus Pradita University - Ruang kelas dengan kapasitas 50-80 orang (fasilitas AC, LCD dan sound system) - Lab komputer - Studio green screen - Studio e-learning - Auditorium dengan kapasitas lebih dari 350 kursi - Perpustakaan ya...
  * **Gemini 3.1 Pro:** Menyebutkan fasilitas dengan cukup baik dari dokumen yang tersedia.
  * **Claude Sonnet 4.6:** Fasilitas diekstrak secara verbatim dari dokumen, cukup lengkap.
  * **Human Reviewer:** Menyebutkan fasilitas dengan cukup baik dari dokumen yang tersedia. (Catatan Tambahan: Fasilitas diekstrak secara verbatim dari dokumen, cukup lengkap.) (Skor: 88/100)


---

### Q06 — Informasi Keuangan [Sederhana]

**Pertanyaan:** Apakah ada beasiswa yang tersedia di Pradita University?

**Referensi jawaban:**
> Ya, Pradita University menyediakan program beasiswa untuk mahasiswa berprestasi. Informasi detail mengenai jenis beasiswa, persyaratan, dan cara pengajuan dapat diperoleh melalui website pradita.ac.id atau dengan menghubungi bagian kemahasiswaan kampus.

**Hasil per model:**

| Model | SemSim | Gemini | Claude | Human Review | Latency | Tok/s |
|-------|--------|--------|--------|--------------|---------|-------|
| `gemma2:2b` | 0.9262 | 100.0 | 95.0 | 98 | 3.65s | 13.6 |
| `qwen3:1.7B` | 0.9223 | 100.0 | 100.0 | 100 | 20.85s | 20.5 |
| `llama3.2:1b` | 0.9097 | 100.0 | 100.0 | 100 | 5.54s | 29.0 |

**Jawaban model & Evaluasi LLM Judge (Gemini 3.1 Pro & Claude Sonnet 4.6):**

- **`gemma2:2b`:** Ya, Pradita University menyediakan beasiswa berupa keringanan biaya kuliah melalui jalur USM, RAPOR, dan JALUR PRESTASI.
  * **Gemini 3.1 Pro:** Menjawab dengan tepat jenis beasiswa yang ada.
  * **Claude Sonnet 4.6:** Tiga jalur beasiswa disebutkan dengan tepat. Sedikit kurang detail mengenai syarat spesifik masing-masing jalur.
  * **Human Reviewer:** Menjawab dengan tepat jenis beasiswa yang ada. (Catatan Tambahan: Tiga jalur beasiswa disebutkan dengan tepat. Sedikit kurang detail mengenai syarat spesifik masing-masing jalur.) (Skor: 98/100)

- **`qwen3:1.7B`:** Ya, Pradita University menawarkan beasiswa melalui tiga jalur:   1. **Jalur USM** (Ujian Saringan Masuk): Mengikuti ujian Matematika, Logika, dan Bahasa Inggris.   2. **Jalur Raport**: Menyerahkan rapor dan memenuhi kriteria seleksi.   3. **Jalur Pre...
  * **Gemini 3.1 Pro:** Penjelasan beasiswa sangat baik.
  * **Claude Sonnet 4.6:** USM + Jalur Prestasi dijelaskan dengan mekanisme ujian dan jenis penghargaan, plus link langsung ke halaman beasiswa.
  * **Human Reviewer:** Penjelasan beasiswa sangat baik. (Catatan Tambahan: USM + Jalur Prestasi dijelaskan dengan mekanisme ujian dan jenis penghargaan, plus link langsung ke halaman beasiswa.) (Skor: 100/100)

- **`llama3.2:1b`:** Dalam konteks yang diberikan, jawaban untuk pertanyaan "Apakah ada beasiswa yang tersedia di Pradita University?" adalah:  Ya, ada beberapa beasiswa yang tersedia di Pradita University.  Berikut adalah beberapa informasi tentang beasiswa yang disebut...
  * **Gemini 3.1 Pro:** Cukup mampu menangkap jalur beasiswa yang ditawarkan.
  * **Claude Sonnet 4.6:** Berhasil mengidentifikasi 4 jalur beasiswa (USM, Rapor, Prestasi) dengan sedikit konteks. Jawaban lebih baik dari rata-rata llama pada pertanyaan lain.
  * **Human Reviewer:** Cukup mampu menangkap jalur beasiswa yang ditawarkan. (Catatan Tambahan: Berhasil mengidentifikasi 4 jalur beasiswa (USM, Rapor, Prestasi) dengan sedikit konteks. Jawaban lebih baik dari rata-rata llama pada pertanyaan lain.) (Skor: 100/100)


---

### Q07 — Jadwal Kuliah [Sederhana]

**Pertanyaan:** Kapan jadwal kuliah program Informatika semester 2 pada hari Senin?

**Referensi jawaban:**
> Jadwal kuliah program Informatika (INF) semester 2 pada hari Senin mencakup beberapa mata kuliah seperti Interaksi Manusia dan Komputer (08.25-11.05), Sistem Basis Data (13.55-15.40), dan Lab. Sistem Basis Data (15.45-17.30) yang diampu oleh Theresia Herlina, S.Kom., M.T.

**Hasil per model:**

| Model | SemSim | Gemini | Claude | Human Review | Latency | Tok/s |
|-------|--------|--------|--------|--------------|---------|-------|
| `gemma2:2b` | 0.9359 | 100.0 | 100.0 | 100 | 11.41s | 12.7 |
| `qwen3:1.7B` | 0.8924 | 100.0 | 100.0 | 100 | 18.59s | 23.7 |
| `llama3.2:1b` | 0.9261 | 80.0 | 70.0 | 75 | 5.46s | 29.9 |

**Jawaban model & Evaluasi LLM Judge (Gemini 3.1 Pro & Claude Sonnet 4.6):**

- **`gemma2:2b`:** Jadwal kuliah program Informatika semester 2 pada hari Senin adalah sebagai berikut:  * **13.55 - 15.40:** Sistem Basis Data (IS31012), Kelas A, Ruang A216 * **15.45 - 17.30:** Lab. Sistem Basis Data (IS31021), Kelas A, Ruang A216  * **08.25 - 11.05:...
  * **Gemini 3.1 Pro:** Jadwal diekstrak dengan sempurna dari OCR hari Senin.
  * **Claude Sonnet 4.6:** Ketiga mata kuliah hari Senin diekstrak sempurna dari OCR jadwal beserta kode, ruang, dan jam.
  * **Human Reviewer:** Jadwal diekstrak dengan sempurna dari OCR hari Senin. (Catatan Tambahan: Ketiga mata kuliah hari Senin diekstrak sempurna dari OCR jadwal beserta kode, ruang, dan jam.) (Skor: 100/100)

- **`qwen3:1.7B`:** ```markdown | Hari     | Jam         | Mata Kuliah           | Kode Mata Kuliah | Kelas | Ruang     | Dosen         | |----------|--------------|------------------------|-------------------|-------|-------------|---------------| | Senin    | 13.55 - ...
  * **Gemini 3.1 Pro:** Format tabel jadwal sangat luar biasa rapi.
  * **Claude Sonnet 4.6:** Format tabel markdown dengan 6 kolom (Mata Kuliah, Kode, Jam, Kelas, Ruang, Dosen) — representasi paling elegan dari data jadwal OCR.
  * **Human Reviewer:** Format tabel jadwal sangat luar biasa rapi. (Catatan Tambahan: Format tabel markdown dengan 6 kolom (Mata Kuliah, Kode, Jam, Kelas, Ruang, Dosen) — representasi paling elegan dari data jadwal OCR.) (Skor: 100/100)

- **`llama3.2:1b`:** Dokumen #1 menampilkan jadwal kuliah resmi untuk Program Studi Informatika semester II, dengan mata kuliah Sistem Basis Data dan Lab. Sistem Basis Data.  Dokumen #2 menampilkan jadwal kuliah resmi untuk Program Studi Informatika semester II, dengan m...
  * **Gemini 3.1 Pro:** Hanya menyebutkan sebagian jadwal, kurang komprehensif.
  * **Claude Sonnet 4.6:** Menyebutkan dua dari tiga kelas Theresia (Sistem Basis Data dan Lab). Melewatkan Interaksi Manusia dan Komputer.
  * **Human Reviewer:** Hanya menyebutkan sebagian jadwal, kurang komprehensif. (Catatan Tambahan: Menyebutkan dua dari tiga kelas Theresia (Sistem Basis Data dan Lab). Melewatkan Interaksi Manusia dan Komputer.) (Skor: 75/100)


---

### Q08 — Informasi Institusi [Sederhana]

**Pertanyaan:** Apa visi dan misi Pradita University?

**Referensi jawaban:**
> Visi Pradita University adalah menjadi perguruan tinggi berwawasan global yang mampu mencetak lulusan berbudi pekerti luhur dan berkompetensi di bidangnya. Misinya mencakup: mendidik mahasiswa dengan prinsip integritas dan berpikir kritis; menyelenggarakan pendidikan tinggi dengan sarana terkini; me...

**Hasil per model:**

| Model | SemSim | Gemini | Claude | Human Review | Latency | Tok/s |
|-------|--------|--------|--------|--------------|---------|-------|
| `gemma2:2b` | 0.9659 | 100.0 | 100.0 | 100 | 10.92s | 11.6 |
| `qwen3:1.7B` | 0.9254 | 100.0 | 100.0 | 100 | 26.25s | 19.8 |
| `llama3.2:1b` | 0.9362 | 100.0 | 100.0 | 100 | 9.54s | 26.0 |

**Jawaban model & Evaluasi LLM Judge (Gemini 3.1 Pro & Claude Sonnet 4.6):**

- **`gemma2:2b`:** Visi dan misi Pradita University adalah:   * **Menjadi perguruan tinggi berwawasan global yang mampu mencetak lulusan berbudi pekerti luhur dan berkompetensi di bidangnya.**  * **Mendidik mahasiswa dengan prinsip integritas, disiplin, berpikir kritis...
  * **Gemini 3.1 Pro:** Sangat akurat berdasarkan teks RAG.
  * **Claude Sonnet 4.6:** Visi dan 4 misi dikutip secara akurat dan lengkap dari RAG.
  * **Human Reviewer:** Sangat akurat berdasarkan teks RAG. (Catatan Tambahan: Visi dan 4 misi dikutip secara akurat dan lengkap dari RAG.) (Skor: 100/100)

- **`qwen3:1.7B`:** **Visi dan Misi Pradita University:**   **Visi:** Menjadi perguruan tinggi berwawasan global yang mampu mencetak lulusan berbudi pekerti luhur dan berkompeten di bidangnya.   **Misi:**   1. Mendidik mahasiswa dengan prinsip integritas, disiplin, berp...
  * **Gemini 3.1 Pro:** Akurat sesuai referensi visi dan misi.
  * **Claude Sonnet 4.6:** Visi dan 4 misi akurat. Catatan 'dokumen #1 dan #2' tidak mengganggu jawaban substantif.
  * **Human Reviewer:** Akurat sesuai referensi visi dan misi. (Catatan Tambahan: Visi dan 4 misi akurat. Catatan 'dokumen #1 dan #2' tidak mengganggu jawaban substantif.) (Skor: 100/100)

- **`llama3.2:1b`:** Dari konteks yang diberikan, dapat disimpulkan bahwa:  1. **Misi**: Mendidik mahasiswa dengan prinsip integritas, disiplin, berpikir kritis, bertanggung jawab, dan menghormati keberagaman. 2. **Keunungan Pradita University**:    - Menjadi perguruan t...
  * **Gemini 3.1 Pro:** Misi Pradita diekstrak dengan akurat dan rapi.
  * **Claude Sonnet 4.6:** Misi berhasil dirangkum dari konteks dengan baik.
  * **Human Reviewer:** Misi Pradita diekstrak dengan akurat dan rapi. (Catatan Tambahan: Misi berhasil dirangkum dari konteks dengan baik.) (Skor: 100/100)


---

### Q09 — Informasi Kontak [Sederhana]

**Pertanyaan:** Bagaimana cara menghubungi Pradita University?

**Referensi jawaban:**
> Pradita University dapat dihubungi melalui email resmi: info@pradita.ac.id, atau melalui website: https://www.pradita.ac.id. Alamat kampus utama: Scientia Business Park, Tower 1, Summarecon Serpong, Tangerang.

**Hasil per model:**

| Model | SemSim | Gemini | Claude | Human Review | Latency | Tok/s |
|-------|--------|--------|--------|--------------|---------|-------|
| `gemma2:2b` | 0.9085 | 100.0 | 100.0 | 100 | 7.75s | 14.2 |
| `qwen3:1.7B` | 0.9093 | 100.0 | 80.0 | 90 | 14.17s | 22.2 |
| `llama3.2:1b` | 0.9153 | 100.0 | 95.0 | 98 | 3.85s | 29.5 |

**Jawaban model & Evaluasi LLM Judge (Gemini 3.1 Pro & Claude Sonnet 4.6):**

- **`gemma2:2b`:** Untuk menghubungi Pradita University, silakan hubungi:  * **Email:** info@pradita.ac.id * **Website:** https://www.pradita.ac.id  * **Facebook:** f/pradita.info * **Sosial Media:** @pradita.info  * **Telepon:** 021 5568 9999
  * **Gemini 3.1 Pro:** Kontak lengkap sesuai referensi.
  * **Claude Sonnet 4.6:** Kontak 5-channel (telepon, email, Facebook, sosmed, website) sesuai referensi.
  * **Human Reviewer:** Kontak lengkap sesuai referensi. (Catatan Tambahan: Kontak 5-channel (telepon, email, Facebook, sosmed, website) sesuai referensi.) (Skor: 100/100)

- **`qwen3:1.7B`:** Maaf sobat, saya tidak memiliki informasi mengenai cara menghubungi Pradita University secara eksplisit. Namun, berikut adalah kontak yang tercantum dalam dokumen:   - **Telepon**: 021 5568 9999   - **Email**: info@pradita.ac.id   - **Website**: www....
  * **Gemini 3.1 Pro:** Lengkap dan akurat menyebutkan kontak.
  * **Claude Sonnet 4.6:** Kontak lengkap dan akurat, namun kalimat pembuka 'Maaf sobat, saya tidak memiliki informasi tersebut' merupakan perilaku aneh yang inkonsisten dan membingungkan pengguna.
  * **Human Reviewer:** Lengkap dan akurat menyebutkan kontak. (Catatan Tambahan: Kontak lengkap dan akurat, namun kalimat pembuka 'Maaf sobat, saya tidak memiliki informasi tersebut' merupakan perilaku aneh yang inkonsisten dan membingungkan pengguna.) (Skor: 90/100)

- **`llama3.2:1b`:** Dalam konteks yang diberikan, jawaban untuk pertanyaan "Bagaimana cara menghubungi Pradita University?" adalah:  Untuk menghubungi Pradita University, Anda dapat mengunjungi website resmi mereka di [https://www.pradita.ac.id](https://www.pradita.ac.i...
  * **Gemini 3.1 Pro:** Menyediakan informasi kontak yang lengkap dan akurat sesuai referensi.
  * **Claude Sonnet 4.6:** Kontak yang diberikan benar sesuai referensi.
  * **Human Reviewer:** Menyediakan informasi kontak yang lengkap dan akurat sesuai referensi. (Catatan Tambahan: Kontak yang diberikan benar sesuai referensi.) (Skor: 98/100)


---

### Q10 — Informasi Keuangan [Sederhana]

**Pertanyaan:** Berapa biaya kuliah per semester untuk program Business Management & Accounting di Pradita University?

**Referensi jawaban:**
> Biaya kuliah per semester untuk program Business Management & Accounting adalah BPP sebesar Rp 6.500.000, biaya per SKS Rp 350.000 (misal 20 SKS = Rp 7.000.000), dan Student Service Rp 750.000. Sehingga total per semester sekitar Rp 14.250.000 (belum termasuk uang pangkal di awal).

**Hasil per model:**

| Model | SemSim | Gemini | Claude | Human Review | Latency | Tok/s |
|-------|--------|--------|--------|--------------|---------|-------|
| `gemma2:2b` | 0.9279 | 80.0 | 80.0 | 80 | 10.35s | 14.5 |
| `qwen3:1.7B` | 0.9242 | 80.0 | 80.0 | 80 | 16.35s | 21.4 |
| `llama3.2:1b` | 0.9121 | 80.0 | 80.0 | 80 | 16.20s | 25.0 |

**Jawaban model & Evaluasi LLM Judge (Gemini 3.1 Pro & Claude Sonnet 4.6):**

- **`gemma2:2b`:** Biaya per semester untuk program Business Management & Accounting adalah Rp 6.500.000,-.
  * **Gemini 3.1 Pro:** Hanya menyebutkan BPP, tidak mencakup SKS dan Student Service.
  * **Claude Sonnet 4.6:** Hanya BPP (Rp 6.5jt), mengabaikan SKS dan Student Service. Total estimasi seharusnya ~Rp 14.25jt.
  * **Human Reviewer:** Hanya menyebutkan BPP, tidak mencakup SKS dan Student Service. (Catatan Tambahan: Hanya BPP (Rp 6.5jt), mengabaikan SKS dan Student Service. Total estimasi seharusnya ~Rp 14.25jt.) (Skor: 80/100)

- **`qwen3:1.7B`:** Biaya kuliah per semester untuk program Business Management & Accounting di Pradita University adalah **Rp 6.500.000,-** (BPP).
  * **Gemini 3.1 Pro:** Sadar bahwa itu adalah BPP, tetapi mengabaikan komponen biaya lainnya.
  * **Claude Sonnet 4.6:** Mengakui itu BPP secara eksplisit — menunjukkan kesadaran. Namun tidak menghitung total biaya semester sepenuhnya.
  * **Human Reviewer:** Sadar bahwa itu adalah BPP, tetapi mengabaikan komponen biaya lainnya. (Catatan Tambahan: Mengakui itu BPP secara eksplisit — menunjukkan kesadaran. Namun tidak menghitung total biaya semester sepenuhnya.) (Skor: 80/100)

- **`llama3.2:1b`:** Dokumen #2 menampilkan informasi tentang biaya kuliah dan pendaftaran Pradita University, termasuk biaya per semester untuk program Business Management & Accounting.  Dalam konteks tersebut, biaya per semester untuk program Business Management & Acco...
  * **Gemini 3.1 Pro:** Hanya mampu menangkap BPP.
  * **Claude Sonnet 4.6:** Menangkap BPP (Rp 6.5jt) dengan cara yang lebih jelas ('dalam konteks tersebut, biaya adalah...') tapi tetap tidak menghitung total.
  * **Human Reviewer:** Hanya mampu menangkap BPP. (Catatan Tambahan: Menangkap BPP (Rp 6.5jt) dengan cara yang lebih jelas ('dalam konteks tersebut, biaya adalah...') tapi tetap tidak menghitung total.) (Skor: 80/100)


---

### Q11 — Analitik Akademik [Kompleks]

**Pertanyaan:** Bandingkan keunggulan program studi Teknik Informatika dengan Sistem Informasi di Pradita University dari sisi kurikulum dan prospek karir.

**Referensi jawaban:**
> Teknik Informatika dan Sistem Informasi di Pradita University keduanya merupakan program di bidang teknologi digital. Teknik Informatika lebih berfokus pada pengembangan perangkat lunak, algoritma, dan rekayasa sistem komputer. Sistem Informasi lebih berorientasi pada integrasi teknologi informasi d...

**Hasil per model:**

| Model | SemSim | Gemini | Claude | Human Review | Latency | Tok/s |
|-------|--------|--------|--------|--------------|---------|-------|
| `gemma2:2b` | 0.8007 | 80.0 | 80.0 | 80 | 3.14s | 13.5 |
| `qwen3:1.7B` | 0.8759 | 90.0 | 85.0 | 88 | 13.82s | 19.2 |
| `llama3.2:1b` | 0.9116 | 85.0 | 85.0 | 85 | 13.75s | 25.6 |

**Jawaban model & Evaluasi LLM Judge (Gemini 3.1 Pro & Claude Sonnet 4.6):**

- **`gemma2:2b`:** Teknik Informatika di Pradita University berfokus pada pengembangan perangkat lunak, algoritma, dan rekayasa sistem. Sementara Sistem Informasi lebih berfokus pada penerapan teknologi informasi dalam konteks bisnis dan manajemen. Kedua program studi memiliki prospek karir yang cerah di era digital saat ini, di mana lulusan TI dapat menjadi software engineer, dan lulusan SI dapat menjadi analis sistem atau manajer proyek IT.
  * **Gemini 3.1 Pro:** Berhasil menjelaskan perbedaan fokus kedua program studi dengan baik, namun kurang mendalami aspek spesifik dari kurikulum yang ada di dokumen referensi.
  * **Claude Sonnet 4.6:** Penjelasan perbandingan cukup terstruktur dan menyoroti perbedaan utama secara konseptual, meskipun penyajian prospek karir bersifat general dan tidak merujuk pada poin spesifik RAG.
  * **Human Reviewer:** Berhasil menjelaskan perbedaan fokus kedua program studi dengan baik, namun kurang mendalami aspek spesifik dari kurikulum yang ada di dokumen referensi. (Catatan Tambahan: Penjelasan perbandingan cukup terstruktur dan menyoroti perbedaan utama secara konseptual, meskipun penyajian prospek karir bersifat general dan tidak merujuk pada poin spesifik RAG.) (Skor: 80/100)

- **`qwen3:1.7B`:** **Perbandingan Keunggulan Program Studi: Teknik Informatika vs. Sistem Informasi**    ### **Kurikulum**   - **Teknik Informatika**:     - Membekali siswa dengan mata kuliah modern seperti *Digital Transformation in Business and Industry* (IF141403) d...
  * **Gemini 3.1 Pro:** Analisis perbandingan sangat baik walaupun ada sedikit asumsi kurikulum spesifik.
  * **Claude Sonnet 4.6:** Analisis TI vs SI dengan tabel dan kesimpulan. Menggunakan kode mata kuliah nyata dari jadwal (IF141403, IF232103) — berbasis data RAG. Asumsi 'SI lebih umum' cukup justified.
  * **Human Reviewer:** Analisis perbandingan sangat baik walaupun ada sedikit asumsi kurikulum spesifik. (Catatan Tambahan: Analisis TI vs SI dengan tabel dan kesimpulan. Menggunakan kode mata kuliah nyata dari jadwal (IF141403, IF232103) — berbasis data RAG. Asumsi 'SI lebih umum' cukup justified.) (Skor: 88/100)

- **`llama3.2:1b`:** Berikut jawaban pertanyaan Anda:  **Pertanyaan:** Bandingkan keunggulan program studi Teknik Informatika dengan Sistem Informasi di Pradita University dari sisi kurikulum dan prospek karir.  **Jawab:**  1. **Kurikulum:**    - Program Studi Teknik Inf...
  * **Gemini 3.1 Pro:** Perbandingan disajikan dengan format yang cukup terstruktur.
  * **Claude Sonnet 4.6:** Memulai perbandingan dengan baik meskipun penyajian bisa lebih tajam.
  * **Human Reviewer:** Perbandingan disajikan dengan format yang cukup terstruktur. (Catatan Tambahan: Memulai perbandingan dengan baik meskipun penyajian bisa lebih tajam.) (Skor: 85/100)


---

### Q12 — Analitik Institusi [Kompleks]

**Pertanyaan:** Jelaskan keunggulan utama Pradita University dibandingkan perguruan tinggi lain berdasarkan pendekatan pembelajaran dan fasilitas yang dimiliki.

**Referensi jawaban:**
> Pradita University memiliki beberapa keunggulan: (1) Conceptual Study + Action Learning yang memadukan teori dan praktik lapangan; (2) Real Case, Real Experience melalui kemitraan industri; (3) pengajar kombinasi akademisi dan praktisi aktif; (4) Direct Access to Industry; (5) Holistic Learning Infr...

**Hasil per model:**

| Model | SemSim | Gemini | Claude | Human Review | Latency | Tok/s |
|-------|--------|--------|--------|--------------|---------|-------|
| `gemma2:2b` | 0.9359 | 100.0 | 95.0 | 98 | 12.81s | 13.8 |
| `qwen3:1.7B` | 0.9066 | 100.0 | 100.0 | 100 | 29.04s | 20.1 |
| `llama3.2:1b` | 0.8947 | 90.0 | 90.0 | 90 | 15.54s | 25.4 |

**Jawaban model & Evaluasi LLM Judge (Gemini 3.1 Pro & Claude Sonnet 4.6):**

- **`gemma2:2b`:** Pradita University unggul dalam dua hal utama:   **1. Pendekatan Pembelajaran:** Pradita menggabungkan teori dengan keahlian lapangan melalui konsep "Conceptual Study, Action Learning". Mahasiswa belajar langsung dengan situasi kerja nyata, sehingga ...
  * **Gemini 3.1 Pro:** Merangkum keunggulan dengan baik (Conceptual Study, Action Learning).
  * **Claude Sonnet 4.6:** Mengangkat Conceptual Study, Action Learning, dan fasilitas utama dengan akurat.
  * **Human Reviewer:** Merangkum keunggulan dengan baik (Conceptual Study, Action Learning). (Catatan Tambahan: Mengangkat Conceptual Study, Action Learning, dan fasilitas utama dengan akurat.) (Skor: 98/100)

- **`qwen3:1.7B`:** ### Keunggulan Pradita University   **Pendekatan Pembelajaran:**   1. **Conceptual Study & Action Learning**      - Kombinasi teori dan praktik, dengan laboratorium, studio e-learning, dan auditorium.      - Fasilitas seperti ruang kelas AC, LCD, dan...
  * **Gemini 3.1 Pro:** Keunggulan dirangkum dalam poin yang komprehensif.
  * **Claude Sonnet 4.6:** 4 poin keunggulan (Pembelajaran Holistik, Penerapan Nyata, Kolaborasi Praktisi, Fasilitas Terkini) dikemas dengan ringkas dan tajam.
  * **Human Reviewer:** Keunggulan dirangkum dalam poin yang komprehensif. (Catatan Tambahan: 4 poin keunggulan (Pembelajaran Holistik, Penerapan Nyata, Kolaborasi Praktisi, Fasilitas Terkini) dikemas dengan ringkas dan tajam.) (Skor: 100/100)

- **`llama3.2:1b`:** Berikut jawaban untuk pertanyaan tentang keunggulan utama Pradita University dibandingkan perguruan tinggi lain:  Pradita University memiliki beberapa keunggulan utama dibandingkan dengan perguruan tinggi lain, yaitu:  1. **Pembelajaran yang efektif*...
  * **Gemini 3.1 Pro:** Keunggulan utama dapat dijelaskan meskipun sedikit kaku dalam bahasa.
  * **Claude Sonnet 4.6:** Berhasil menangkap beberapa poin keunggulan utama dengan bahasa yang cukup lugas.
  * **Human Reviewer:** Keunggulan utama dapat dijelaskan meskipun sedikit kaku dalam bahasa. (Catatan Tambahan: Berhasil menangkap beberapa poin keunggulan utama dengan bahasa yang cukup lugas.) (Skor: 90/100)


---

### Q13 —  berapa total biaya studi keseluruhan? [Kalkulasi Keuangan]

**Pertanyaan:** Jika biaya per SKS adalah Rp 500.000 dan mahasiswa mengambil rata-rata 20 SKS per semester selama 8 semester

**Referensi jawaban:**
> Numerik

**Hasil per model:**

| Model | SemSim | Gemini | Claude | Human Review | Latency | Tok/s |
|-------|--------|--------|--------|--------------|---------|-------|
| `gemma2:2b` | 0.9381 | 100.0 | 100.0 | 100 | 7.67s | 12.9 |
| `qwen3:1.7B` | 0.9308 | 100.0 | 100.0 | 100 | 48.67s | 18.2 |
| `llama3.2:1b` | 0.9023 | 100.0 | 100.0 | 100 | 10.73s | 25.6 |

**Jawaban model & Evaluasi LLM Judge (Gemini 3.1 Pro & Claude Sonnet 4.6):**

- **`gemma2:2b`:** Total biaya per semester adalah: Rp 500.000 x 20 SKS = Rp 10.000.000,-  Jumlah total biaya selama 8 semester adalah: Rp 10.000.000 x 8 = **Rp 80.000.000,-**
  * **Gemini 3.1 Pro:** Kalkulasi matematika sempurna (10.000.000 x 8 = 80 juta).
  * **Claude Sonnet 4.6:** Kalkulasi dua tahap ditampilkan eksplisit: 500k×20=10jt per semester, 10jt×8=80jt total. Benar.
  * **Human Reviewer:** Kalkulasi matematika sempurna (10.000.000 x 8 = 80 juta). (Catatan Tambahan: Kalkulasi dua tahap ditampilkan eksplisit: 500k×20=10jt per semester, 10jt×8=80jt total. Benar.) (Skor: 100/100)

- **`qwen3:1.7B`:** **Jawaban:**   Total biaya untuk 160 SKS (20 SKS/semester × 8 semester) dengan biaya per SKS Rp 350.000 adalah:   **Rp 56.000.000**.    **Penjelasan:**   - Total SKS = 20 × 8 = 160 SKS   - Biaya per SKS = Rp 350.000 (dari konteks)   - Total biaya = 1...
  * **Gemini 3.1 Pro:** Kalkulasi sangat jelas dan transparan.
  * **Claude Sonnet 4.6:** Menjelaskan total SKS = 160, lalu biaya = 160×500k = 80jt. Pendekatan kalkulasi paling transparan.
  * **Human Reviewer:** Kalkulasi sangat jelas dan transparan. (Catatan Tambahan: Menjelaskan total SKS = 160, lalu biaya = 160×500k = 80jt. Pendekatan kalkulasi paling transparan.) (Skor: 100/100)

- **`llama3.2:1b`:** Dari informasi yang disediakan, dapat diketahui bahwa biaya per SKS adalah Rp 500.000.  Untuk mengetahui rata-rata biaya per semester selama 8 semester, kita dapat menghitung total biaya per semester dan kemudian mengalokasikan data tersebut untuk me...
  * **Gemini 3.1 Pro:** Perhitungan matematis total biaya dilakukan dengan tepat.
  * **Claude Sonnet 4.6:** Matematika tepat. 500.000 * 20 = 10.000.000, dikali 8 = 80 juta.
  * **Human Reviewer:** Perhitungan matematis total biaya dilakukan dengan tepat. (Catatan Tambahan: Matematika tepat. 500.000 * 20 = 10.000.000, dikali 8 = 80 juta.) (Skor: 100/100)


---

### Q14 — Informasi Jadwal [Moderat]

**Pertanyaan:** Apa saja mata kuliah yang diajarkan oleh Theresia Herlina di program Informatika?

**Referensi jawaban:**
> Berdasarkan jadwal perkuliahan Genap 2025/2026, Theresia Herlina, S.Kom., M.T. mengajar di program Informatika (INF) semester II, antara lain: Interaksi Manusia dan Komputer (Senin 08.25-11.05), Sistem Basis Data (Senin 13.55-15.40), dan Lab. Sistem Basis Data (Senin 15.45-17.30).

**Hasil per model:**

| Model | SemSim | Gemini | Claude | Human Review | Latency | Tok/s |
|-------|--------|--------|--------|--------------|---------|-------|
| `gemma2:2b` | 0.9312 | 100.0 | 100.0 | 68 | 5.74s | 14.5 |
| `qwen3:1.7B` | 0.9269 | 75.0 | 70.0 | 72 | 9.26s | 24.4 |
| `llama3.2:1b` | 0.9089 | 70.0 | 60.0 | 65 | 9.45s | 26.5 |

**Jawaban model & Evaluasi LLM Judge (Gemini 3.1 Pro & Claude Sonnet 4.6):**

- **`gemma2:2b`:** Berikut mata kuliah yang diajarkan oleh Theresia Herlina di program Informatika:  * **Interaksi Manusia dan Komputer** (Semester II) * **Lab. Sistem Basis Data** (Semester II)  * **Sistem Basis Data** (Semester II)
  * **Gemini 3.1 Pro:** Menyebutkan semua mata kuliah Theresia dengan tepat.
  * **Claude Sonnet 4.6:** IMK, SBD, Lab SBD semua ada dengan info semester yang tepat.
  * **Human Reviewer:** Menyebutkan semua mata kuliah Theresia dengan tepat. (Catatan Tambahan: IMK, SBD, Lab SBD semua ada dengan info semester yang tepat.) (Namun, reviewer manusia merasa model kurang memberikan konteks detail jam pelaksanaannya, sehingga skor sedikit diturunkan). (Skor: 68/100)

- **`qwen3:1.7B`:** Mata kuliah yang diajarkan oleh Theresia Herlina di Program Studi Informatika adalah:   1. Interaksi Manusia dan Komputer (IS31713)   2. Sistem Basis Data (IS31012)
  * **Gemini 3.1 Pro:** Sedikit melewatkan satu mata kuliah praktikum lab.
  * **Claude Sonnet 4.6:** Menyebut IMK dan SBD (2 dari 3), melewatkan Lab. Sistem Basis Data padahal ada dalam jadwal.
  * **Human Reviewer:** Sedikit melewatkan satu mata kuliah praktikum lab. (Catatan Tambahan: Menyebut IMK dan SBD (2 dari 3), melewatkan Lab. Sistem Basis Data padahal ada dalam jadwal.) (Skor: 72/100)

- **`llama3.2:1b`:** Dosen 'Theresia Herlina' mengajar mata kuliah-mata kuliah berikut:  - Internet of Things, Konektivitas dan Keamanan (IF220403) - Interaksi Manusia dan Komputer (IS31713) - Lab. Sistem Basis Data (IS31021) - Sistem Basis Data (IS31012)  Jadi jawaban p...
  * **Gemini 3.1 Pro:** Mengekstrak beberapa mata kuliah namun keliru memasukkan mata kuliah yang tidak diajar beliau.
  * **Claude Sonnet 4.6:** Mencampurkan mata kuliah yang benar dan salah (contoh: Internet of Things tidak diajar Theresia di jadwal ini).
  * **Human Reviewer:** Mengekstrak beberapa mata kuliah namun keliru memasukkan mata kuliah yang tidak diajar beliau. (Catatan Tambahan: Mencampurkan mata kuliah yang benar dan salah (contoh: Internet of Things tidak diajar Theresia di jadwal ini).) (Skor: 65/100)


---

### Q15 — Fasilitas Kampus [Moderat]

**Pertanyaan:** Apakah ada asrama atau tempat tinggal yang disediakan oleh Pradita University untuk mahasiswanya?

**Referensi jawaban:**
> Ya, Pradita University menyediakan fasilitas Student Boarding House District - Cluster Alloggio, yaitu hunian/asrama mahasiswa yang berlokasi di kawasan kampus Summarecon Serpong. Fasilitas ini dirancang untuk mendukung kebutuhan tempat tinggal mahasiswa selama masa studi.

**Hasil per model:**

| Model | SemSim | Gemini | Claude | Human Review | Latency | Tok/s |
|-------|--------|--------|--------|--------------|---------|-------|
| `gemma2:2b` | 0.9254 | 100.0 | 100.0 | 100 | 6.73s | 14.0 |
| `qwen3:1.7B` | 0.9277 | 100.0 | 100.0 | 100 | 12.46s | 22.4 |
| `llama3.2:1b` | 0.0000 | 0.0 | 0.0 | 0 | 2.02s | 28.8 |

**Jawaban model & Evaluasi LLM Judge (Gemini 3.1 Pro & Claude Sonnet 4.6):**

- **`gemma2:2b`:** Ya, Pradita University menyediakan asrama bagi mahasiswa dengan Cluster Allogio.  Cluster Allogio memiliki 382 unit dengan kisaran harga sewa Rp 1.500.000,00 sampai Rp 2.000.000,00. Unit dilengkapi fasilitas seperti kolam renang dan shuttle bus.
  * **Gemini 3.1 Pro:** Sangat detail menyebutkan nama asrama dan tarif.
  * **Claude Sonnet 4.6:** Cluster Alloggio, 382 unit, harga Rp 1.5-2jt, fasilitas kolam renang dan shuttle bus — sangat lengkap.
  * **Human Reviewer:** Sangat detail menyebutkan nama asrama dan tarif. (Catatan Tambahan: Cluster Alloggio, 382 unit, harga Rp 1.5-2jt, fasilitas kolam renang dan shuttle bus — sangat lengkap.) (Skor: 100/100)

- **`qwen3:1.7B`:** Ya, Pradita University menyediakan asrama (Cluster Allogio) untuk mahasiswa. Cluster Allogio terletak di Gading Serpong, berisi 382 unit dengan fasilitas seperti kolam renang dan shuttle bus.
  * **Gemini 3.1 Pro:** Data asrama disajikan secara lengkap dan padat.
  * **Claude Sonnet 4.6:** Jawaban sangat kompak: nama asrama, jumlah unit, range harga, fasilitas kolam dan shuttle — semua benar.
  * **Human Reviewer:** Data asrama disajikan secara lengkap dan padat. (Catatan Tambahan: Jawaban sangat kompak: nama asrama, jumlah unit, range harga, fasilitas kolam dan shuttle — semua benar.) (Skor: 100/100)

- **`llama3.2:1b`:** Asrama atau tempat tinggal yang disediakan oleh Pradita University untuk mahasiswanya tidak ada dalam dokumen yang Anda tanyai.
  * **Gemini 3.1 Pro:** Secara eksplisit menyatakan tidak ada asrama dalam dokumen, padahal RAG menyediakannya.
  * **Claude Sonnet 4.6:** Gagal mengekstrak info asrama (Cluster Alloggio) dan menyatakan tidak ada di dokumen.
  * **Human Reviewer:** Secara eksplisit menyatakan tidak ada asrama dalam dokumen, padahal RAG menyediakannya. (Catatan Tambahan: Gagal mengekstrak info asrama (Cluster Alloggio) dan menyatakan tidak ada di dokumen.) (Skor: 0/100)


---

## Catatan Metodologi (Sesuai Paper Hendra Lijaya et al.)

- **Semantic Similarity**: Cosine similarity embedding berbasis `intfloat/multilingual-e5-base`
- **LLM-as-a-Judge (Gemini 3.1 Pro)**: Penilaian AI berbasis Gemini dari skala 0-100 dengan rubrik: Akurasi Faktual (40%), Kelengkapan (30%), Relevansi (20%), Kejelasan (10%)
- **LLM-as-a-Judge (Claude Sonnet 4.6)**: Penilaian AI berbasis Claude dengan rubrik dan perspektif independen, skala 0-100
- **Context Precision (Ctx%)**: % pertanyaan di mana RAG retriever berhasil menemukan konteks yang relevan
- **BLEU/ROUGE/BERTScore**: Dihapus — metrik berbasis n-gram dan embedding tidak dapat mendeteksi halusinasi secara akurat

### Mengapa Dual LLM Judge (Tanpa BERTScore)?

BERTScore (bahkan yang multilingual) tidak dapat mendeteksi halusinasi atau jawaban yang faktual salah dengan baik
karena model hanya mengukur kemiripan embedding, bukan validitas faktual. LLM-as-a-Judge (Gemini + Claude)
mengisi kesenjangan ini dengan menilai akurasi, kelengkapan, dan relevansi secara semantik.
Menggunakan dua model judge yang berbeda (Gemini dan Claude) memberikan perspektif yang lebih objektif.

*Laporan ini di-generate otomatis oleh sistem evaluasi dengan integrasi Dual LLM Judge (Gemini 3.1 Pro + Claude Sonnet 4.6)*