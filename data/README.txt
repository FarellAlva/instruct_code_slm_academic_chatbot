# Pradita University Knowledge Base

Place PDF files in this directory. They will be automatically
discovered and ingested by the RAG pipeline.

## How to add knowledge:

1. Copy your PDF files here (e.g., katalog_2024.pdf, panduan_mahasiswa.pdf)
2. Run the ingestion script from the project root:

   python ingest.py

3. Or run the ingestion_pipeline.ipynb notebook for step-by-step visibility.

## Notes:
- Only .pdf files are processed (other formats are ignored)
- Re-running ingest.py will upsert (update) existing chunks safely
- Use `python ingest.py --clear` to wipe the DB and start fresh
- End-users CANNOT upload files — only developers manage this folder
