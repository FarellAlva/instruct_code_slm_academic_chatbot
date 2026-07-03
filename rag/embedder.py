"""
rag/embedder.py — Local embedding function using SentenceTransformers.

No OpenAI API. Runs entirely on-device.

NOTE on multilingual-e5-small:
  The E5 model family requires a task prefix for optimal accuracy:
  - For documents stored in ChromaDB  → prefix with 'passage: '
  - For query strings at search time  → prefix with 'query: '
  Without the prefix, the model produces significantly degraded embeddings.
"""

from sentence_transformers import SentenceTransformer
from chromadb import EmbeddingFunction, Documents, Embeddings
from config import EMBEDDING_MODEL


class LocalEmbeddingFunction(EmbeddingFunction):
    """
    ChromaDB-compatible embedding function backed by SentenceTransformers.
    Handles the E5-family 'query:'/'passage:' prefix convention automatically.
    """

    def __init__(self, model_name: str = EMBEDDING_MODEL):
        import torch
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"[Embedder] 🔄 Loading embedding model: {model_name} on {device.upper()}")
        self._model = SentenceTransformer(model_name, device=device)
        # Detect E5 family by model name so we can prepend the required prefixes
        self._is_e5 = "e5" in model_name.lower()
        print(f"[Embedder] ✅ Model loaded (E5 prefix mode: {self._is_e5}).")

    def _add_passage_prefix(self, texts):
        """Wrap each document with E5 passage prefix if needed."""
        if self._is_e5:
            return [f"passage: {t}" if not t.startswith("passage: ") else t for t in texts]
        return texts

    def _add_query_prefix(self, text: str) -> str:
        """Wrap a query string with E5 query prefix if needed."""
        if self._is_e5:
            return f"query: {text}" if not text.startswith("query: ") else text
        return text

    def __call__(self, input: Documents) -> Embeddings:
        """Called by ChromaDB when ingesting/storing documents — passage prefix."""
        prefixed = self._add_passage_prefix(list(input))
        embeddings = self._model.encode(prefixed, show_progress_bar=False)
        return embeddings.tolist()

    def embed_query(self, text: str = None, input=None, **kwargs) -> list:
        """Convenience method for single-query embedding — query prefix."""
        query_text = input if input is not None else text
        if query_text is None and len(kwargs) > 0:
            query_text = list(kwargs.values())[0]

        # Chroma dynamically calls embed_query when searching and passes a LIST.
        if isinstance(query_text, list):
            prefixed = [self._add_query_prefix(t) for t in query_text]
            return self._model.encode(prefixed).tolist()

        return self._model.encode([self._add_query_prefix(query_text)])[0].tolist()

    def embed_texts(self, texts: list) -> list:
        """Embed a list of texts (passages) and return list of vectors."""
        prefixed = self._add_passage_prefix(texts)
        return self._model.encode(prefixed, show_progress_bar=True).tolist()


# Module-level singleton so the model is only loaded once per process.
_embedding_fn: LocalEmbeddingFunction | None = None


def get_embedding_function() -> LocalEmbeddingFunction:
    global _embedding_fn
    if _embedding_fn is None:
        _embedding_fn = LocalEmbeddingFunction()
    return _embedding_fn
