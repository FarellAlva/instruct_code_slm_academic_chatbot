"""
rag/scraper.py — Scrape content and images from the Pradita University website.

This module:
1. Scrapes text content from key pages on pradita.ac.id
2. Downloads facility images into data/images/
3. Saves scraped text as structured .txt files in data/web/
4. All scraped content is then available for RAG ingestion

Usage:
    python -m rag.scraper          # scrape everything
    python -m rag.scraper --skip-images   # text only
"""

import os
import re
import time
import requests
from pathlib import Path
from typing import List, Dict, Any
from urllib.parse import urljoin

# ─── Configuration ────────────────────────────────────────────────────────────

BASE_URL = "https://www.pradita.ac.id"

# Pages to scrape for text content
PAGES_TO_SCRAPE = [
    {"url": "/", "name": "homepage"},
    {"url": "/about/pradita-university", "name": "about"},
    {"url": "/student-facilities", "name": "student_facilities"},
    {"url": "/scholarship", "name": "scholarship"},
    {"url": "/admission/enrollment-information", "name": "enrollment"},
    {"url": "/admission/enrollment", "name": "enrollment_procedure"},
    {"url": "/student-service", "name": "student_service"},
]

# Facility images scraped from the student-facilities page
FACILITY_IMAGES = [
    # ─── Learning Facilities ──────────────────────────────────────────────
    {
        "name": "Auditorium - Pradita University",
        "category": "Learning Facilities",
        "url": "https://pradita-s3.s3.ap-southeast-3.amazonaws.com/prod/webpradita/post/thumb/auditorium-pradita-institute__Ceg30.jpg",
    },
    {
        "name": "Classroom - Pradita University",
        "category": "Learning Facilities",
        "url": "https://pradita-s3.s3.ap-southeast-3.amazonaws.com/prod/webpradita/post/thumb/classroom-pradita-university__Prr80.jpg",
    },
    {
        "name": "Mac Laboratorium - Pradita University",
        "category": "Learning Facilities",
        "url": "https://pradita-s3.s3.ap-southeast-3.amazonaws.com/prod/webpradita/post/thumb/mac-laboratorium-pradita-university__XPqH5.jpg",
    },
    {
        "name": "Computer Laboratorium - Pradita University",
        "category": "Learning Facilities",
        "url": "https://pradita-s3.s3.ap-southeast-3.amazonaws.com/prod/webpradita/post/thumb/computer-laboratorium-pradita-university__O4clg.jpg",
    },
    {
        "name": "Drawing Lab - Pradita University",
        "category": "Learning Facilities",
        "url": "https://pradita-s3.s3.ap-southeast-3.amazonaws.com/prod/webpradita/post/thumb/drawing-lab-pradita-university__PCX2s.jpg",
    },
    {
        "name": "Library - Pradita University",
        "category": "Learning Facilities",
        "url": "https://pradita-s3.s3.ap-southeast-3.amazonaws.com/prod/webpradita/post/thumb/library-pradita-university__hIQnG.jpg",
    },
    {
        "name": "Pradita Research & Innovation Center",
        "category": "Learning Facilities",
        "url": "https://pradita-s3.s3.ap-southeast-3.amazonaws.com/prod/webpradita/post/thumb/pradita-research-and-innovation-center-pradita-university__e6ISk.jpg",
    },
    {
        "name": "Photography Lab - Pradita Research & Innovation Center",
        "category": "Learning Facilities",
        "url": "https://pradita-s3.s3.ap-southeast-3.amazonaws.com/prod/webpradita/post/thumb/photography-lab-pradita-research-innovation-center__7hAQa.jpg",
    },
    {
        "name": "Workshop Lab - Pradita Research & Innovation Center",
        "category": "Learning Facilities",
        "url": "https://pradita-s3.s3.ap-southeast-3.amazonaws.com/prod/webpradita/post/thumb/workshop-room-pradita-research-innovation-center__6ftRV.jpg",
    },
    {
        "name": "Podcast Room - Pradita University",
        "category": "Learning Facilities",
        "url": "https://pradita-s3.s3.ap-southeast-3.amazonaws.com/prod/webpradita/post/thumb/podcast-room-pradita-university__fnlet.jpg",
    },
    # ─── Hospitality & Tourism Labs ───────────────────────────────────────
    {
        "name": "Front Office Practice Area - Hospitality & Tourism Lab",
        "category": "Hospitality & Tourism Labs",
        "url": "https://pradita-s3.s3.ap-southeast-3.amazonaws.com/prod/webpradita/post/thumb/front-office-practice-area-hospitality-tourism-lab__X5AM5.jpg",
    },
    {
        "name": "Hotel Practice Area - Hospitality & Tourism Lab",
        "category": "Hospitality & Tourism Labs",
        "url": "https://pradita-s3.s3.ap-southeast-3.amazonaws.com/prod/webpradita/post/thumb/hotel-practice-area-hospitality-tourism-lab__tlTOd.jpg",
    },
    {
        "name": "Kitchen Practice Area - Hospitality & Tourism Lab",
        "category": "Hospitality & Tourism Labs",
        "url": "https://pradita-s3.s3.ap-southeast-3.amazonaws.com/prod/webpradita/post/thumb/kitchen-practice-area-hospitality-tourism-lab__4zKez.jpg",
    },
    {
        "name": "Kitchen Theater - Hospitality & Tourism Lab",
        "category": "Hospitality & Tourism Labs",
        "url": "https://pradita-s3.s3.ap-southeast-3.amazonaws.com/prod/webpradita/post/thumb/kitchen-theater-hospitality-tourism-lab__8o2SN.jpg",
    },
    {
        "name": "Mixology Laboratorium - Hospitality & Tourism Lab",
        "category": "Hospitality & Tourism Labs",
        "url": "https://pradita-s3.s3.ap-southeast-3.amazonaws.com/prod/webpradita/post/thumb/mixology-laboratorium-hospitality-tourism-lab__5zt5w.jpg",
    },
    {
        "name": "Wine Laboratory - Hospitality & Tourism Lab",
        "category": "Hospitality & Tourism Labs",
        "url": "https://pradita-s3.s3.ap-southeast-3.amazonaws.com/prod/webpradita/post/thumb/wine-laboratory-hospitality-tourism-lab__99K1c.jpg",
    },
    {
        "name": "Coffee and Tea Laboratory - Hospitality & Tourism Lab",
        "category": "Hospitality & Tourism Labs",
        "url": "https://pradita-s3.s3.ap-southeast-3.amazonaws.com/prod/webpradita/post/thumb/coffee-and-tea-laboratory-hospitality-tourism-lab__sYd5s.jpg",
    },
    # ─── Housing & Transportation ─────────────────────────────────────────
    {
        "name": "Student Boarding House District - Cluster Alloggio",
        "category": "Housing & Transportation",
        "url": "https://pradita-s3.s3.ap-southeast-3.amazonaws.com/prod/webpradita/post/image/student-boarding-house-district-cluster-alloggio__jcmY2.jpg",
    },
    {
        "name": "Bedroom - Student Boarding House District",
        "category": "Housing & Transportation",
        "url": "https://pradita-s3.s3.ap-southeast-3.amazonaws.com/prod/webpradita/post/image/bedroom-student-boarding-house-district__bfnDR.jpg",
    },
    {
        "name": "Shuttle Bus - Pradita University",
        "category": "Housing & Transportation",
        "url": "https://pradita-s3.s3.ap-southeast-3.amazonaws.com/prod/webpradita/post/image/shuttle-bus-pradita-university__40Kq8.jpg",
    },
    # ─── Sport, Leisure & Wellness ────────────────────────────────────────
    {
        "name": "Sport Court - Pradita University",
        "category": "Sport, Leisure & Wellness",
        "url": "https://pradita-s3.s3.ap-southeast-3.amazonaws.com/prod/webpradita/post/image/sport-court-pradita-university__rHK11.jpg",
    },
    {
        "name": "Summarecon Mall Serpong",
        "category": "Sport, Leisure & Wellness",
        "url": "https://pradita-s3.s3.ap-southeast-3.amazonaws.com/prod/webpradita/post/image/summarecon-mall-serpong__2aHbO.jpg",
    },
    {
        "name": "Scientia Square Park",
        "category": "Sport, Leisure & Wellness",
        "url": "https://pradita-s3.s3.ap-southeast-3.amazonaws.com/prod/webpradita/post/image/scientia-square-park__fzAB9.jpg",
    },
    {
        "name": "Swimming Pool - The Springs Club",
        "category": "Sport, Leisure & Wellness",
        "url": "https://pradita-s3.s3.ap-southeast-3.amazonaws.com/prod/webpradita/post/image/swimming-pool-the-springs-club__P9qxy.jpg",
    },
]


# ─── Helper functions ─────────────────────────────────────────────────────────

def _clean_text(raw: str) -> str:
    """Remove excessive whitespace and navigation junk from scraped text."""
    # Remove URLs in brackets and markdown link syntax
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', raw)
    # Collapse multiple blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Remove leading/trailing whitespace per line
    lines = [line.strip() for line in text.split('\n')]
    text = '\n'.join(lines)
    return text.strip()


def download_image(url: str, save_path: str) -> bool:
    """Download a single image. Returns True on success."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.pradita.ac.id/",
        "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
    }
    try:
        resp = requests.get(url, timeout=30, stream=True, headers=headers)
        resp.raise_for_status()
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        with open(save_path, 'wb') as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except Exception as e:
        print(f"  ❌ Failed to download {url}: {e}")
        return False


def download_all_facility_images(image_dir: str) -> List[Dict[str, str]]:
    """
    Download all facility images to image_dir.
    Returns list of dicts with name, category, local_path.
    """
    os.makedirs(image_dir, exist_ok=True)
    results = []

    print(f"\n[Scraper] 🖼  Downloading {len(FACILITY_IMAGES)} facility images…")
    for i, img in enumerate(FACILITY_IMAGES, 1):
        # Create a clean filename
        slug = re.sub(r'[^a-zA-Z0-9]+', '_', img['name']).strip('_').lower()
        ext  = img['url'].rsplit('.', 1)[-1].split('?')[0]  # jpg/png
        filename = f"{slug}.{ext}"
        save_path = os.path.join(image_dir, filename)

        if os.path.exists(save_path):
            print(f"  [{i}/{len(FACILITY_IMAGES)}] ✅ Already exists: {filename}")
            ok = True
        else:
            print(f"  [{i}/{len(FACILITY_IMAGES)}] ⬇  {img['name']}…")
            ok = download_image(img['url'], save_path)
            time.sleep(0.3)  # polite delay

        if ok:
            results.append({
                "name":       img["name"],
                "category":   img["category"],
                "local_path": save_path,
                "filename":   filename,
                "url":        img["url"],
            })

    print(f"[Scraper] ✅ Downloaded {len(results)}/{len(FACILITY_IMAGES)} images.")
    return results


def generate_facilities_knowledge(image_dir: str) -> str:
    """
    Generate a structured text document about Pradita University facilities
    that includes image references for the chatbot.
    """
    lines = [
        "# Pradita University Student Facilities",
        "",
        "Pradita University menyediakan berbagai fasilitas lengkap untuk menunjang kegiatan belajar dan kehidupan mahasiswa.",
        "",
        "## FASILITAS KAMPUS",
        "Gedung kampus Pradita University dilengkapi dengan fasilitas-fasilitas sebagai berikut:",
        "- Ruang kelas dengan kapasitas 50-80 orang (fasilitas AC, LCD dan sound system)",
        "- Lab komputer",
        "- Studio green screen",
        "- Studio e-learning",
        "- Auditorium dengan kapasitas lebih dari 350 kursi",
        "- Perpustakaan yang lengkap dengan koleksi lebih dari 2000 buku",
        "- Fasilitas Student Club (mulai dari sarana olahraga hingga aktivitas peminatan)",
        "- High-speed wi-fi connectivity",
        "- Green environment, lingkungan kampus yang hijau dengan taman dan danau",
        "",
    ]

    # Group images by category
    categories = {}
    for img in FACILITY_IMAGES:
        cat = img["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(img)

    for cat, items in categories.items():
        lines.append(f"## {cat.upper()}")
        lines.append("")
        for item in items:
            slug = re.sub(r'[^a-zA-Z0-9]+', '_', item['name']).strip('_').lower()
            ext  = item['url'].rsplit('.', 1)[-1].split('?')[0]
            filename = f"{slug}.{ext}"
            lines.append(f"### {item['name']}")
            # Only the bare filename is recorded: an absolute path would be
            # machine-specific, and it ends up inside the LLM's retrieved
            # context, making the model recite raw filesystem paths to users.
            # app.py resolves the real path from BASE_DIR at render time.
            lines.append(f"Gambar fasilitas: {filename}")
            lines.append(f"URL asli: {item['url']}")
            lines.append("")

    # Transportation info
    lines.extend([
        "## TRANSPORTASI",
        "Pradita University menyediakan shuttle bus untuk mahasiswa.",
        "Distrik mahasiswa di Cluster Allogio yang didirikan oleh Summarecon Serpong "
        "dibangun khusus untuk sarana tempat tinggal bagi mahasiswa selama menempuh masa perkuliahan.",
        "Cluster Allogio memiliki jumlah unit sebanyak 382 unit dengan kisaran harga sewa "
        "Rp 1.500.000,00 sampai Rp 2.000.000,00, yang dilengkapi dengan fasilitas cluster yaitu "
        "kolam renang dan shuttle bus.",
        "",
        "## WELLNESS",
        "Pusat hiburan dan lifestyle di kawasan Summarecon Serpong yang memiliki kawasan total "
        "seluas 110.000 m2, lengkap dengan lebih dari 350 tenant yang terdiri dari: "
        "fashion & accessories, bag & shoes, health & beauty, sports & lifestyle, electronics, "
        "IT & gadgets, kids, toys & maternity, supermarket & department store, home & furnishing, "
        "specialist shop & services, entertainments, food & beverages, food court, "
        "downtown walk, salsa food city, alfresco dining.",
        "",
        "## LOKASI KAMPUS",
        "",
        "### Jakarta Campus",
        "Menara Satu Building",
        "Jl. Boulevard Raya LA 3 No.1, Sentra Kelapa Gading, Jakarta Utara, DKI Jakarta 14240",
        "",
        "### Gading Serpong Campus",
        "Scientia Business Park, Tower 1",
        "Jalan Raya Boulevard Blok 0/1, Summarecon Serpong, Kabupaten Tangerang, Banten 15810",
        "",
        "## KONTAK",
        "Email: info@pradita.ac.id",
        "Website: https://www.pradita.ac.id",
    ])

    return '\n'.join(lines)


def generate_programs_knowledge() -> str:
    """Generate structured text about Pradita University academic programs."""
    return """# Program Studi Pradita University

## JENJANG SARJANA (S1) - BACHELOR'S DEGREE

Pradita University menawarkan program studi S1 berikut:

### 1. Architecture (Arsitektur)
Website: https://www.pradita.ac.id/programs/architecture

### 2. Urban Planning (Perencanaan Kota)
Website: https://www.pradita.ac.id/programs/urban-planning

### 3. Civil Engineering (Teknik Sipil)
Website: https://www.pradita.ac.id/programs/civil-enginer

### 4. Interior Design (Desain Interior)
Website: https://www.pradita.ac.id/programs/interior-design

### 5. Visual Communication Design (Desain Komunikasi Visual / DKV)
Website: https://www.pradita.ac.id/programs/visual-communication-design

### 6. Accounting (Akuntansi)
Website: https://www.pradita.ac.id/programs/accounting

### 7. Management (Manajemen)
Website: https://www.pradita.ac.id/programs/bussiness-management

### 8. Informatics (Informatika / Teknik Informatika)
Website: https://www.pradita.ac.id/programs/information-technology

### 9. Business Information System (Sistem Informasi Bisnis)
Website: https://www.pradita.ac.id/programs/business-information-system

### 10. Hospitality & Tourism (Perhotelan & Pariwisata)
Website: https://www.pradita.ac.id/programs/hospitality-tourism

## JENJANG DIPLOMA (D3) - DIPLOMA DEGREE

### 1. Culinary Arts (Seni Kuliner)
Website: https://www.pradita.ac.id/programs/culinary-arts

## JENJANG MAGISTER (S2) - MASTER DEGREE

### 1. Information Technology (Teknologi Informasi)
Website: https://www.pradita.ac.id/programs/information-technology-s2

## TOTAL PROGRAM STUDI
- S1 (Bachelor's): 10 program studi
- D3 (Diploma): 1 program studi
- S2 (Master): 1 program studi
- Total: 12 program studi
"""


def generate_about_knowledge(base_dir: str = "") -> str:
    """Generate structured text about Pradita University overview (reads existing file if present)."""
    if base_dir:
        existing_path = os.path.join(base_dir, "data", "web", "about_pradita.txt")
        if os.path.exists(existing_path):
            with open(existing_path, "r", encoding="utf-8") as f:
                return f.read().strip()
    # Fallback to base text if file does not exist yet
    return """# Tentang Pradita University

## SEJARAH DAN LATAR BELAKANG
Pradita University lahir dari jaringan korporasi berbagai industri yang diprakarsai oleh Summarecon dan mitra bisnis korporasinya. Pendidikan kepada mahasiswa ditegakkan dengan fondasi budi pekerti, demi melahirkan generasi yang cerdas dan menjunjung tinggi moral, serta berorientasi pada landasan teori yang kuat dan keahlian praktis yang sesuai kebutuhan industri. Sehingga akan lahir talenta bangsa yang siap bekerja, berkarya, serta bernilai tinggi di tengah persaingan industri yang sengit, baik sebagai profesional maupun entrepreneur.

## VISI
Menjadi perguruan tinggi berwawasan global yang mampu mencetak lulusan berbudi pekerti luhur dan berkompetensi di bidangnya.

## MISI
1. Mendidik mahasiswa dengan prinsip integritas, disiplin, berpikir kritis, bertanggung jawab, dan menghormati keberagaman.
2. Menyelenggarakan kegiatan pendidikan tinggi dengan sarana dan lingkungan belajar yang efektif, efisien, dan terkini sesuai dengan perkembangan global.
3. Mengembangkan penelitian tepat guna yang berkontribusi positif bagi industri dan masyarakat.
4. Melakukan pengabdian masyarakat untuk membentuk lulusan yang memiliki kepedulian sosial.

## KEUNGGULAN PRADITA UNIVERSITY

### 1. Conceptual Study, Action Learning
Pradita memadukan penguasaan teori dan keahlian lapangan dengan harmonis. Dengan begitu, ilmu yang diajarkan kepada mahasiswa merupakan pelajaran terkini yang relevan dengan situasi kerja nanti.

### 2. Real Case, Real Experience
Pembelajaran yang efektif harus dilandasi dengan prinsip kurikulum "belajar langsung sebagaimana sesungguhnya terjadi di kehidupan nyata". Mahasiswa akan mendapatkan pengalaman kerja nyata dengan sejumlah mitra perusahaan Pradita University.

### 3. Experienced Academician x Active Practitioner
Pradita University mengkombinasikan pengajar dengan latar belakang praktisi yang masih aktif dan akademisi berpengalaman dengan berkolaborasi bersama mitra perusahaan untuk membekali mahasiswa dari sudut pandang praktisi.

### 4. Direct Access to Industry and Professional World
Mahasiswa akan mendapatkan pengalaman kerja nyata dengan sejumlah mitra perusahaan Pradita University.

### 5. Holistic Learning Infrastructure
Lingkungan sekitar kampus harus nyaman dan fasilitasnya dapat menunjang kegiatan mahasiswa. Kawasan Summarecon Serpong seluas ratusan hektar akan menjadi lab untuk studi sekaligus tempat yang asyik buat menjalani aktivitas lainnya.

## LOKASI KAMPUS

### Jakarta Campus
Menara Satu Building
Jl. Boulevard Raya LA 3 No.1, Sentra Kelapa Gading, Jakarta Utara, DKI Jakarta 14240

### Gading Serpong Campus (Kampus Utama)
Scientia Business Park, Tower 1
Jalan Raya Boulevard Blok 0/1, Summarecon Serpong, Kabupaten Tangerang, Banten 15810

## KONTAK
Email: info@pradita.ac.id
Website: https://www.pradita.ac.id
"""


def generate_scholarship_knowledge() -> str:
    """Generate structured text about Pradita University scholarships."""
    return """# Beasiswa Pradita University

Pradita University memberikan BEASISWA berupa keringanan biaya kuliah kepada calon mahasiswa melalui jalur sebagai berikut:

## 1. JALUR UJIAN SARINGAN MASUK (USM)
Mengikuti Ujian Saringan Masuk (USM) dengan mata pelajaran:
- Matematika
- Logika
- Bahasa Inggris

Ujian akan dijadwalkan oleh education counsellor secara online.
Semakin tinggi nilai USM, semakin besar kesempatan memperoleh keringanan biaya kuliah.

## 2. JALUR RAPOR
Mengikuti seleksi dengan menyerahkan rapor dan dapatkan keringanan biaya kuliah apabila memenuhi kriteria seleksi.

## 3. JALUR PRESTASI
Bagi siswa-siswi berprestasi secara akademik atau non-akademik, dapat mengikuti seleksi dengan menyerahkan penghargaan berupa:
- Sertifikat
- Medali
- Piala

Di tingkat nasional atau internasional. Dapatkan keringanan biaya kuliah apabila lulus seleksi beasiswa jalur prestasi.

## CARA MENDAFTAR
Kunjungi: https://www.pradita.ac.id/admission/enrollment-information
Atau hubungi: info@pradita.ac.id
"""


def generate_enrollment_knowledge() -> str:
    """Generate structured text about enrollment."""
    return """# Informasi Pendaftaran Pradita University

## PROSEDUR PENDAFTARAN
Silahkan mengisi informasi yang diperlukan untuk mendapatkan brosur, rincian harga, dan panduan pendaftaran.

## LINK PENDAFTARAN
Website Pendaftaran: https://www.pradita.ac.id/admission/enrollment-information
Prosedur Enrollment: https://www.pradita.ac.id/admission/enrollment

## INFORMASI PENTING
- Kalender Akademik: https://www.pradita.ac.id/admission/calender_akademik
- Beasiswa: https://www.pradita.ac.id/scholarship
- Layanan Mahasiswa: https://www.pradita.ac.id/student-service

## KONTAK PENDAFTARAN
Email: info@pradita.ac.id
Website: https://www.pradita.ac.id
"""


def generate_jadwal_panduan_knowledge() -> str:
    """Generate structured text acting as a dictionary for decoding Schedule PDFs."""
    return """# Panduan Membaca Data Jadwal & Kode Pradita University

## KODE PROGRAM STUDI
- INF: Informatika
- TI: Teknik Informatika
- SI: Sistem Informasi
- PAR: Perhotelan & Pariwisata
- PWK: Perencanaan Wilayah dan Kota (Urban Planning)
- AR: Arsitektur
- TS: Teknik Sipil
- DKV: Desain Komunikasi Visual
- DI: Desain Interior
- SK: Seni Kuliner

## KODE DAN SINGKATAN KELAS
- KMK: Kode Mata Kuliah.
- SKS: Bobot SKS matakuliah.
- Kelas a + b: Artinya kelas A dan kelas B digabung karena mahasiswanya banyak.
- Gabung (contoh: gabung SI + PAR): Artinya kelas tersebut digabung antara mahasiswa jurusan Sistem Informasi dan Pariwisata.

## KODE RUANG (CONTOH: a306)
- Huruf pertama (contoh 'a'): Merupakan penanda gedung atau tipe ruang.
- Angka pertama (contoh '3'): Menunjukkan Lantai ruangan tersebut berada (contoh: Lantai 3).
- Dua angka terakhir (contoh '06'): Menunjukkan nomor kelas di lantai tersebut.
"""

# ─── Main orchestrator ────────────────────────────────────────────────────────

def run_scraper(base_dir: str, skip_images: bool = False) -> None:
    """
    Main entry point — scrape all content and save to data/ directory.
    """
    web_dir   = os.path.join(base_dir, "data", "web")
    image_dir = os.path.join(base_dir, "data", "images")
    os.makedirs(web_dir, exist_ok=True)

    print("=" * 60)
    print("  Pradita University — Web Scraper")
    print("=" * 60)

    # 1. Generate and save structured knowledge files
    knowledge_files = {
        "about_pradita.txt":     generate_about_knowledge(base_dir),
        "programs.txt":          generate_programs_knowledge(),
        "facilities.txt":        generate_facilities_knowledge(image_dir),
        "scholarship.txt":       generate_scholarship_knowledge(),
        "enrollment.txt":        generate_enrollment_knowledge(),
        "panduan_jadwal.txt":    generate_jadwal_panduan_knowledge(),
    }

    print(f"\n[Scraper] 📝 Saving {len(knowledge_files)} knowledge files…")
    for fname, content in knowledge_files.items():
        fpath = os.path.join(web_dir, fname)
        with open(fpath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  ✅ {fname} ({len(content)} chars)")

    # 2. Download facility images
    if not skip_images:
        downloaded = download_all_facility_images(image_dir)
        # Save image manifest
        manifest_path = os.path.join(image_dir, "manifest.txt")
        with open(manifest_path, 'w', encoding='utf-8') as f:
            f.write("# Pradita University Facility Images Manifest\n")
            f.write(f"# Total images: {len(downloaded)}\n\n")
            for img in downloaded:
                f.write(f"{img['filename']} | {img['name']} | {img['category']}\n")
        print(f"\n[Scraper] 📋 Image manifest saved to {manifest_path}")
    else:
        print("\n[Scraper] ⏭  Skipping image download (--skip-images)")

    print("\n" + "=" * 60)
    print("  ✅ Scraping complete!")
    print(f"  Text files : {web_dir}")
    if not skip_images:
        print(f"  Images     : {image_dir}")
    print("=" * 60)


# ─── CLI ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    import sys

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

    parser = argparse.ArgumentParser(description="Scrape Pradita University website")
    parser.add_argument("--skip-images", action="store_true",
                        help="Skip downloading facility images")
    parser.add_argument("--base-dir", default=os.path.join(os.path.dirname(__file__), ".."),
                        help="Project root directory")
    args = parser.parse_args()

    run_scraper(args.base_dir, args.skip_images)
