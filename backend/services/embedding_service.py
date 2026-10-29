"""
Embedding service: converts text to dense vectors for semantic similarity.

Primary backend: sentence-transformers (all-MiniLM-L6-v2, 384 dims).
Fallback backend: scikit-learn TF-IDF with character + word n-grams.

Both backends expose the same interface:
  compute_similarity(text_a, text_b) -> float in [0, 1]
  get_backend_name()                 -> "sentence-transformers" | "tfidf"

Embeddings are cached in memory (keyed by MD5 hash) for the sentence-
transformers backend. The TF-IDF backend is stateless per call.
"""
import hashlib
import logging
import threading
from typing import Optional

import numpy as np

_logger = logging.getLogger(__name__)

# ── Backend detection ──────────────────────────────────────────────────────────

_ST_AVAILABLE = False
try:
    from sentence_transformers import SentenceTransformer as _SentenceTransformer
    _ST_AVAILABLE = True
except ImportError:
    _logger.warning(
        "sentence-transformers not available; falling back to TF-IDF similarity. "
        "Install with: pip install sentence-transformers"
    )

# ── Sentence-transformers singleton ───────────────────────────────────────────

_MODEL_NAME = "all-MiniLM-L6-v2"
_model: Optional[object] = None
_model_lock = threading.Lock()
_model_load_failed = False

# Embedding cache: md5(text) → normalized numpy vector
_cache: dict[str, np.ndarray] = {}


def _get_st_model():
    global _model, _model_load_failed
    if _model is not None:
        return _model
    if _model_load_failed:
        return None
    with _model_lock:
        if _model is not None:
            return _model
        if _model_load_failed:
            return None
        try:
            _model = _SentenceTransformer(_MODEL_NAME)
            _logger.info("Loaded sentence-transformer model: %s", _MODEL_NAME)
        except Exception as exc:
            _model_load_failed = True
            _logger.warning("Failed to load sentence-transformer model: %s", exc)
            return None
    return _model


def _st_encode(text: str) -> Optional[np.ndarray]:
    key = hashlib.md5(text.encode("utf-8", errors="replace")).hexdigest()
    if key in _cache:
        return _cache[key]
    model = _get_st_model()
    if model is None:
        return None
    vec = model.encode(text, normalize_embeddings=True)
    vec = np.array(vec, dtype=np.float32)
    _cache[key] = vec
    return vec


# ── TF-IDF fallback ────────────────────────────────────────────────────────────

def _tfidf_similarity(text_a: str, text_b: str) -> float:
    """Fit a TF-IDF vectorizer on the two texts and return cosine similarity."""
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity as sk_cos

    if not text_a.strip() or not text_b.strip():
        return 0.0
    try:
        vec = TfidfVectorizer(
            analyzer="word",
            ngram_range=(1, 2),
            sublinear_tf=True,
            min_df=1,
        )
        tfidf = vec.fit_transform([text_a.lower(), text_b.lower()])
        sim = sk_cos(tfidf[0:1], tfidf[1:2])[0, 0]
        return float(np.clip(sim, 0.0, 1.0))
    except Exception as exc:
        _logger.debug("TF-IDF similarity failed: %s", exc)
        return 0.0


# ── Public API ─────────────────────────────────────────────────────────────────

def get_backend_name() -> str:
    if _ST_AVAILABLE and _get_st_model() is not None:
        return "sentence-transformers"
    return "tfidf"


def compute_similarity(text_a: str, text_b: str) -> float:
    """
    Return cosine similarity between two texts in [0, 1].
    Uses sentence-transformers if available, TF-IDF otherwise.
    Never raises — returns 0.0 on any error.
    """
    if not text_a or not text_b:
        return 0.0
    if text_a.strip().lower() == text_b.strip().lower():
        return 1.0

    if _ST_AVAILABLE:
        vec_a = _st_encode(text_a)
        vec_b = _st_encode(text_b)
        if vec_a is not None and vec_b is not None:
            sim = float(np.dot(vec_a, vec_b))
            return float(np.clip(sim, 0.0, 1.0))

    return _tfidf_similarity(text_a, text_b)
