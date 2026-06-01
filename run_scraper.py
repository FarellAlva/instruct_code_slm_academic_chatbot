"""Quick standalone runner for the scraper — no rag package import needed."""
import sys, os

# Fix Windows console encoding for emoji
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the scraper module directly (not through rag/__init__.py)
import importlib.util
spec = importlib.util.spec_from_file_location("scraper", "rag/scraper.py")
scraper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scraper)

if __name__ == "__main__":
    scraper.run_scraper(os.path.dirname(os.path.abspath(__file__)))
