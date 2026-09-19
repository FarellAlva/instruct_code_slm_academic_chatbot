# Adita AI (Docker)

### 1. Clone Repository

```bash
git clone https://github.com/FarellAlva/instruct_code.git
cd instruct_code
```

### 2. Jalankan Docker Compose

```bash
docker compose up -d --build
```

Docker akan mengunduh base image, melakukan build container aplikasi, memproses dokumen knowledge base ke ChromaDB, dan menyalakan semua service di latar belakang.

### 3. Setup Model Ollama

Pilih salah satu metode berikut:

#### Opsi A: Model Cloud (Default: gemma4:31b-cloud)
Memerlukan akun Ollama (gratis). Setup hanya perlu dijalankan satu kali:

1. Hubungkan akun:
```bash
docker compose exec ollama ollama signin
```
Buka tautan `https://ollama.com/...` yang tampil di terminal melalui browser, login, lalu klik tombol Approve.

2. Unduh model cloud:
```bash
docker compose exec ollama ollama pull gemma4:31b-cloud
```

*Catatan: Sesi login dan file model tersimpan permanen di volume Docker `ollama_models`. Anda tidak perlu login ulang saat komputer dimatikan atau direstart.*

#### Opsi B: Model Lokal (100% Offline / Tanpa Akun)
Jika ingin berjalan secara lokal tanpa membuat akun:

1. Unduh model open-source lokal:
```bash
docker compose exec ollama ollama pull gemma2:2b
```

2. Pada aplikasi web (kolom pengaturan di sidebar kiri), ubah nama model menjadi:
```text
gemma2:2b
```

### 4. Akses Aplikasi

Buka browser dan akses alamat berikut:
```text
http://localhost:8501
```

---

## Perintah Operasional Harian

| Kebutuhan | Perintah |
| :--- | :--- |
| Menyalakan kembali sistem | `docker compose up -d` |
| Mematikan seluruh sistem | `docker compose down` |
| Cek status container | `docker compose ps` |
| Pantau log aplikasi chat | `docker compose logs -f adita-chat` |
| Pantau log Ollama | `docker compose logs -f ollama` |
| Pantau seluruh log sistem | `docker compose logs -f` |

### Pembaruan Knowledge Base

- Membangun ulang index ChromaDB dari folder `data/`:
```bash
docker compose run --rm adita-ingest python ingest.py --clear --skip-scrape
docker compose restart adita-chat
```

- Scraping ulang website Pradita lalu bangun ulang index:
```bash
docker compose run --rm adita-ingest python ingest.py --clear
docker compose restart adita-chat
```

---

## Troubleshooting

- **Port 8501 atau 11434 bentrok:**
  Ubah port host pada `docker-compose.yml`, misalnya `"8502:8501"`, kemudian akses melalui `http://localhost:8502`.
- **Docker daemon tidak merespons:**
  Pastikan Docker Desktop sudah dibuka dan berstatus "Engine running".
- **Bot tidak menemukan informasi jadwal/kampus:**
  Jalankan pembaruan index knowledge base:
  ```bash
  docker compose run --rm adita-ingest python ingest.py --clear --skip-scrape
  docker compose restart adita-chat
  ```
