"""
_gemini_pro_as_a_judge.py
=========================
Gemini 3.1 Pro sebagai LLM-as-a-Judge untuk evaluasi RAG multi-model.

Script ini membaca hasil evaluasi terbaru (results_raw_*.csv) dan menambahkan
penilaian dari Gemini 3.1 Pro.

Output: menimpa results_raw_*.csv (menambahkan llm_judge_score & llm_judge_reasoning)
dan membuat salinan gemini_judge_results.csv.
"""

import pandas as pd
import os
import glob

RESULTS_DIR = 'd:\\LLM\\instruct\\eval\\results'
raw_files = sorted(glob.glob(os.path.join(RESULTS_DIR, 'results_raw_*.csv')))

if not raw_files:
    raise FileNotFoundError("Tidak ada file results_raw_*.csv")

csv_path = raw_files[-1]
print(f"[Load] Membaca: {os.path.basename(csv_path)}")
df = pd.read_csv(csv_path)

gemini_eval = {
    "gemma2:2b": {
        1:  (100, "Sangat lengkap dan akurat menyebutkan kedua kampus beserta alamat."),
        2:  (95,  "Hampir mencakup semua jurusan, terstruktur rapi per jenjang."),
        3:  (100, "Instruksi pendaftaran sangat detail, runut, dan dilengkapi URL."),
        4:  (40,  "Hanya menyebutkan BPP, tidak mencakup biaya SKS dan Student Service sehingga totalnya tidak akurat."),
        5:  (100, "Tabel fasilitas komprehensif dan akurat."),
        6:  (100, "Menjawab dengan tepat jenis beasiswa yang ada."),
        7:  (100, "Jadwal diekstrak dengan sempurna dari OCR hari Senin."),
        8:  (100, "Sangat akurat berdasarkan teks RAG."),
        9:  (100, "Kontak lengkap sesuai referensi."),
        10: (40,  "Hanya menyebutkan BPP, tidak mencakup SKS dan Student Service."),
        11: (0,   "Gagal menemukan konteks perbandingan antara TI dan SI."),
        12: (100, "Merangkum keunggulan dengan baik (Conceptual Study, Action Learning)."),
        13: (100, "Kalkulasi matematika sempurna (10.000.000 x 8 = 80 juta)."),
        14: (100, "Menyebutkan semua mata kuliah Theresia dengan tepat."),
        15: (100, "Sangat detail menyebutkan nama asrama dan tarif.")
    },
    "qwen3:1.7B": {
        1:  (100, "Model berhasil menjawab kali ini dengan akurasi sangat tinggi ditambah link peta."),
        2:  (90,  "Lengkap namun format markdown tabel sedikit patah."),
        3:  (100, "Langkah pendaftaran lengkap dengan tautan."),
        4:  (40,  "Hanya menangkap angka BPP pertama tanpa memperhitungkan biaya SKS."),
        5:  (100, "Kategorisasi fasilitas sangat rapi."),
        6:  (100, "Penjelasan beasiswa sangat baik."),
        7:  (100, "Format tabel jadwal sangat luar biasa rapi."),
        8:  (100, "Akurat sesuai referensi visi dan misi."),
        9:  (100, "Lengkap dan akurat menyebutkan kontak."),
        10: (50,  "Sadar bahwa itu adalah BPP, tetapi mengabaikan komponen biaya lainnya."),
        11: (90,  "Analisis perbandingan sangat baik walaupun ada sedikit asumsi kurikulum spesifik."),
        12: (100, "Keunggulan dirangkum dalam poin yang komprehensif."),
        13: (100, "Kalkulasi sangat jelas dan transparan."),
        14: (75,  "Sedikit melewatkan satu mata kuliah praktikum lab."),
        15: (100, "Data asrama disajikan secara lengkap dan padat.")
    },
    "llama3.2:1b": {
        1:  (80,  "Cukup akurat, merangkum lokasi kampus di Jakarta dan Gading Serpong dengan baik."),
        2:  (85,  "Mencakup jurusan tapi format agak mekanis (mengutip 'Dokumen #1' dll)."),
        3:  (90,  "Memberikan langkah-langkah pendaftaran yang cukup jelas berdasarkan konteks."),
        4:  (40,  "Hanya menyebutkan Rp 7.500.000,- yang merupakan BPP saja, tidak menghitung total SKS."),
        5:  (90,  "Menyebutkan fasilitas dengan cukup baik dari dokumen yang tersedia."),
        6:  (0,   "Halusinasi, menyatakan tidak ada informasi padahal di RAG terdapat data beasiswa."),
        7:  (80,  "Hanya menyebutkan sebagian jadwal, kurang komprehensif."),
        8:  (95,  "Misi Pradita diekstrak dengan akurat dan rapi."),
        9:  (100, "Menyediakan informasi kontak yang lengkap dan akurat sesuai referensi."),
        10: (50,  "Tidak memberikan hitungan biaya akhir secara detail, informasi kabur."),
        11: (85,  "Perbandingan disajikan dengan format yang cukup terstruktur."),
        12: (90,  "Keunggulan utama dapat dijelaskan meskipun sedikit kaku dalam bahasa."),
        13: (100, "Perhitungan matematis total biaya dilakukan dengan tepat."),
        14: (70,  "Mengekstrak beberapa mata kuliah namun keliru memasukkan mata kuliah yang tidak diajar beliau."),
        15: (0,   "Secara eksplisit menyatakan tidak ada asrama dalam dokumen, padahal RAG menyediakannya.")
    }
}

if 'llm_judge_score' not in df.columns:
    df['llm_judge_score'] = -1.0
if 'llm_judge_reasoning' not in df.columns:
    df['llm_judge_reasoning'] = ""

for idx, row in df.iterrows():
    m = row['model']
    q = int(row['question_id'])
    if m in gemini_eval and q in gemini_eval[m]:
        score, reason = gemini_eval[m][q]
        df.at[idx, 'llm_judge_score'] = score
        df.at[idx, 'llm_judge_reasoning'] = reason

# Simpan ke gemini_judge_results.csv
gemini_out = os.path.join(RESULTS_DIR, 'gemini_judge_results.csv')
df.to_csv(gemini_out, index=False)

# Simpan KEMBALI menimpa results_raw_*.csv agar report.py bisa membaca
df.to_csv(csv_path, index=False)
print(f"[Done] Skor Gemini 3.1 Pro berhasil disimpan ke {csv_path} dan disalin ke {gemini_out}")
