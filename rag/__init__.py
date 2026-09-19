# rag/__init__.py
import sys
# Workaround for NumPy 2.x optional binary extensions in pandas
sys.modules['bottleneck'] = None
sys.modules['numexpr'] = None

from .loader    import load_pdfs, load_web_texts, load_all
from .chunker   import chunk_documents, SCHEDULE_FILES
from .embedder  import get_embedding_function
from .store     import get_chroma_collection, add_documents_to_db
from .retriever import retrieve_context
from .scraper   import run_scraper, FACILITY_IMAGES

__all__ = [
    "load_pdfs",
    "load_web_texts",
    "load_all",
    "chunk_documents",
    "SCHEDULE_FILES",
    "get_embedding_function",
    "get_chroma_collection",
    "add_documents_to_db",
    "retrieve_context",
    "run_scraper",
    "FACILITY_IMAGES",
]
