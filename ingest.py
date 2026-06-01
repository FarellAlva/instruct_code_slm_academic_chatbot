"""
ingest.py — Developer CLI script to ingest knowledge into ChromaDB.

Usage:
    python ingest.py                    # scrape web + ingest all (PDFs + web text)
    python ingest.py --clear            # wipe collection before ingesting
    python ingest.py --skip-scrape      # skip web scraping, only ingest existing files
    python ingest.py --skip-images      # scrape text but skip downloading images
    python ingest.py --data-dir ./docs  # custom data directory
"""

import argparse
import sys
import os

# Fix Windows console encoding for emoji
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Ensure project root is on the path when run directly
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import DATA_DIR, CHROMA_DIR, BASE_DIR
from rag.loader   import load_all
from rag.chunker  import chunk_documents
from rag.store    import get_chroma_collection, add_documents_to_db, clear_collection
from rag.scraper  import run_scraper


def run_ingestion(
    data_dir: str,
    do_clear: bool = False,
    do_scrape: bool = True,
    skip_images: bool = False,
) -> None:
    print("=" * 60)
    print("  Pradita University — RAG Ingestion Pipeline")
    print("=" * 60)

    # 0. Scrape website content first (if requested)
    if do_scrape:
        print("\n[Ingest] 🌐 Step 0: Scraping Pradita University website…")
        run_scraper(BASE_DIR, skip_images=skip_images)

    # 1. Connect to (or create) the vector store
    collection = get_chroma_collection(CHROMA_DIR)

    if do_clear:
        print("\n[Ingest] 🗑  Clearing existing collection…")
        clear_collection(collection)

    # 2. Load ALL sources (PDFs + web text files)
    print(f"\n[Ingest] 📂 Loading documents from: {data_dir}")
    documents = load_all(data_dir)
    if not documents:
        print("[Ingest] ⚠  No content to ingest. Add PDFs to /data/ or run scraper first.")
        return

    # 3. Chunk (auto-selects strategy per file type)
    print("\n[Ingest] ✂️  Chunking documents (smart strategy per file type)…")
    chunks = chunk_documents(documents)

    # 4. Store
    print("\n[Ingest] 💾 Storing chunks in ChromaDB…")
    add_documents_to_db(chunks, collection)

    print("\n" + "=" * 60)
    print(f"  ✅ Ingestion complete! {collection.count()} chunks in DB.")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Ingest knowledge into the Pradita RAG knowledge base."
    )
    parser.add_argument(
        "--data-dir",
        default=DATA_DIR,
        help="Path to folder containing PDF files (default: ./data)",
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear the existing collection before ingesting",
    )
    parser.add_argument(
        "--skip-scrape",
        action="store_true",
        help="Skip web scraping, only ingest existing files",
    )
    parser.add_argument(
        "--skip-images",
        action="store_true",
        help="Scrape text but skip downloading facility images",
    )
    args = parser.parse_args()
    run_ingestion(
        args.data_dir,
        do_clear=args.clear,
        do_scrape=not args.skip_scrape,
        skip_images=args.skip_images,
    )


if __name__ == "__main__":
    main()
