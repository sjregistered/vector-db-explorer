"""
Embeddings Module – Vector DB Explorer
Generates embeddings for text documents using sentence-transformers.
Provides embedding visualization utilities.
"""

import logging
from typing import List, Optional

import numpy as np

logger = logging.getLogger(__name__)

# Global model instance (lazy-loaded)
_model = None
_model_name = "all-MiniLM-L6-v2"


def get_model():
    """Lazy-load the sentence-transformer model."""
    global _model
    if _model is None:
        logger.info(f"Loading embedding model: {_model_name}")
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(_model_name)
        logger.info("Embedding model loaded.")
    return _model


def generate_embeddings(texts: List[str]) -> List[List[float]]:
    """
    Generate embeddings for a list of texts.

    Args:
        texts: List of text strings.

    Returns:
        List of embedding vectors.
    """
    if not texts:
        return []
    model = get_model()
    embeddings = model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
    return embeddings.tolist()


def generate_single_embedding(text: str) -> List[float]:
    """Generate embedding for a single text."""
    model = get_model()
    return model.encode(text, convert_to_numpy=True).tolist()


def _get_dimension(model) -> int:
    """Embedding dimension, compatible with old and new sentence-transformers."""
    if hasattr(model, "get_embedding_dimension"):
        return model.get_embedding_dimension()
    return model.get_sentence_embedding_dimension()


def get_embedding_info() -> dict:
    """Return embedding model information."""
    model = get_model()
    return {
        "model_name": _model_name,
        "dimension": _get_dimension(model),
        "max_seq_length": model.max_seq_length,
    }


def compute_similarity_matrix(
    texts: List[str],
    embeddings: Optional[List[List[float]]] = None
) -> List[List[float]]:
    """
    Compute pairwise cosine similarity matrix for a list of texts.

    Args:
        texts: List of text strings.
        embeddings: Optional precomputed embeddings (avoids re-encoding).

    Returns:
        2D list of similarity scores.
    """
    if not texts:
        return []

    if embeddings is None:
        embeddings = generate_embeddings(texts)
    embeddings = np.array(embeddings)
    # Normalize
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1
    normalized = embeddings / norms
    # Cosine similarity = dot product of normalized vectors
    sim_matrix = np.dot(normalized, normalized.T)
    return sim_matrix.tolist()


def reduce_dimensions(embeddings: List[List[float]], method: str = "pca", n_components: int = 2) -> List[List[float]]:
    """
    Reduce embedding dimensions for visualization.

    Args:
        embeddings: List of embedding vectors.
        method: 'pca' or 'random' projection.
        n_components: Target dimensions (2 or 3).

    Returns:
        List of reduced-dimension vectors.
    """
    if not embeddings:
        return []

    arr = np.array(embeddings)

    if method == "pca":
        # Simple PCA without sklearn dependency
        mean = np.mean(arr, axis=0)
        centered = arr - mean
        cov = np.cov(centered.T)
        eigenvalues, eigenvectors = np.linalg.eigh(cov)
        # Take top n_components eigenvectors
        idx = np.argsort(eigenvalues)[::-1][:n_components]
        components = eigenvectors[:, idx]
        reduced = np.dot(centered, components)
    else:
        # Random projection
        np.random.seed(42)
        projection = np.random.randn(arr.shape[1], n_components)
        projection /= np.linalg.norm(projection, axis=0)
        reduced = np.dot(arr, projection)

    return reduced.tolist()
