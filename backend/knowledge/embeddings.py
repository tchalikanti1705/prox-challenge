"""
Embeddings layer - generates vector embeddings for semantic search.

Supports:
1. OpenAI embeddings (text-embedding-3-small, 1536 dims) - best quality
2. TF-IDF embeddings - no external API needed, decent quality

At startup, rebuilds the TF-IDF vocabulary from loaded chunks so
query embedding works without re-extraction.

Pre-computes a normalized numpy matrix for O(1) batch cosine similarity.
"""
import json
import math
import re
from collections import Counter
import numpy as np
from typing import List, Dict, Optional
from config import USE_OPENAI_EMBEDDINGS, OPENAI_API_KEY


# =========== Module-level state ===========
_idf_scores: Dict[str, float] = {}
_vocabulary: List[str] = []

# Pre-computed normalized embedding matrix (set by build_search_index)
_embedding_matrix: Optional[np.ndarray] = None  # shape: (n_chunks, dim)
_embedding_dim: int = 0


# =========== Tokenizer ===========
_STOP_WORDS = frozenset({
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "need", "must", "and", "or",
    "but", "if", "then", "than", "that", "this", "these", "those", "it",
    "its", "of", "in", "on", "at", "to", "for", "with", "by", "from",
    "as", "into", "about", "not", "no", "so", "up", "out", "all", "also",
    "each", "any", "when", "what", "which", "who", "how", "where", "there",
    "here", "more", "some", "only", "very", "just", "one", "two", "see",
})


def _tokenize(text: str) -> List[str]:
    """Tokenize text into lowercase words, removing short/stop words."""
    words = re.findall(r'[a-z][a-z0-9\-]{1,}', text.lower())
    return [w for w in words if w not in _STOP_WORDS]


# =========== TF-IDF ===========

def _build_tfidf_vocabulary(chunks: List[Dict], max_features: int = 500) -> tuple:
    """Build TF-IDF vocabulary from corpus. Returns (vocabulary, idf_scores)."""
    n_docs = len(chunks)
    doc_freq = Counter()

    for chunk in chunks:
        tokens = set(_tokenize(chunk["text"]))
        for token in tokens:
            doc_freq[token] += 1

    filtered = {
        term: count for term, count in doc_freq.items()
        if count >= 2 and count < n_docs * 0.9
    }
    vocab = sorted(filtered, key=lambda t: filtered[t], reverse=True)[:max_features]
    idf = {term: math.log(n_docs / (filtered[term] + 1)) + 1 for term in vocab}

    return vocab, idf


def rebuild_tfidf_vocabulary(chunks: List[Dict]):
    """
    Rebuild TF-IDF vocabulary from already-loaded chunks.
    
    Called at startup so query embedding works without re-extraction.
    Only needed for TF-IDF mode (OpenAI embeddings don't need this).
    """
    global _idf_scores, _vocabulary

    if not chunks:
        return

    # Check if chunks have TF-IDF embeddings (not OpenAI 1536-dim)
    sample_emb = chunks[0].get("embedding", [])
    if len(sample_emb) > 600:
        # These are OpenAI embeddings — no TF-IDF vocab needed
        return

    _vocabulary, _idf_scores = _build_tfidf_vocabulary(chunks)
    if _vocabulary:
        print(f"  ✓ Rebuilt TF-IDF vocabulary ({len(_vocabulary)} terms)")


# =========== Pre-computed search index ===========

def build_search_index(chunks: List[Dict]):
    """
    Pre-compute a normalized embedding matrix for fast batch similarity.
    
    Single matrix multiply replaces N individual cosine_similarity calls.
    Called once at startup after chunks are loaded.
    """
    global _embedding_matrix, _embedding_dim

    embeddings = [c["embedding"] for c in chunks if "embedding" in c]
    if not embeddings:
        _embedding_matrix = None
        return

    mat = np.array(embeddings, dtype=np.float32)
    norms = np.linalg.norm(mat, axis=1, keepdims=True)
    norms[norms == 0] = 1.0  # Avoid division by zero
    _embedding_matrix = mat / norms
    _embedding_dim = _embedding_matrix.shape[1]
    print(f"  ✓ Built search index ({_embedding_matrix.shape[0]} chunks × {_embedding_dim} dims)")


def batch_cosine_similarity(query_embedding: List[float]) -> np.ndarray:
    """
    Compute cosine similarity between query and ALL chunks at once.
    
    Returns array of scores, one per chunk. Uses the pre-computed matrix.
    Falls back to individual cosine_similarity if matrix not built.
    """
    global _embedding_matrix

    if _embedding_matrix is None:
        return np.array([])

    q = np.array(query_embedding, dtype=np.float32)
    norm = np.linalg.norm(q)
    if norm == 0:
        return np.zeros(_embedding_matrix.shape[0])

    q_normalized = q / norm
    # Single matrix multiply: O(n*d) instead of n separate dot products
    return _embedding_matrix @ q_normalized


# =========== Embedding generation (extraction time) ===========

def generate_embeddings(chunks: List[Dict]) -> List[Dict]:
    """Add embedding vectors to each chunk."""
    global _idf_scores, _vocabulary

    print("🔢 Generating embeddings...")

    if USE_OPENAI_EMBEDDINGS:
        return generate_with_openai(chunks)

    return generate_with_tfidf(chunks)


def generate_with_openai(chunks: List[Dict]) -> List[Dict]:
    """Generate embeddings using OpenAI's embedding API."""
    try:
        from openai import OpenAI

        if not OPENAI_API_KEY:
            print("  ⚠️ OPENAI_API_KEY not set, falling back to TF-IDF")
            return generate_with_tfidf(chunks)

        client = OpenAI(api_key=OPENAI_API_KEY)
        texts = [chunk["text"][:8191] for chunk in chunks]

        # Batch in groups of 100 (API limit is 2048)
        batch_size = 100
        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            response = client.embeddings.create(
                model="text-embedding-3-small",
                input=batch,
            )
            all_embeddings.extend([e.embedding for e in response.data])

        for chunk, emb in zip(chunks, all_embeddings):
            chunk["embedding"] = emb

        print(f"  ✓ Generated {len(chunks)} OpenAI embeddings (1536 dims)")
        return chunks
    except Exception as e:
        print(f"  ⚠️ OpenAI embedding failed: {e}, falling back to TF-IDF")
        return generate_with_tfidf(chunks)


def generate_with_tfidf(chunks: List[Dict]) -> List[Dict]:
    """Generate TF-IDF embeddings (no external API needed)."""
    global _idf_scores, _vocabulary

    _vocabulary, _idf_scores = _build_tfidf_vocabulary(chunks)
    vocab_index = {term: i for i, term in enumerate(_vocabulary)}
    dim = len(_vocabulary)

    for chunk in chunks:
        tokens = _tokenize(chunk["text"])
        tf = Counter(tokens)
        total = len(tokens) if tokens else 1

        vector = [0.0] * dim
        for token, count in tf.items():
            if token in vocab_index:
                vector[vocab_index[token]] = (count / total) * _idf_scores.get(token, 1.0)

        chunk["embedding"] = vector

    print(f"  ✓ Generated {len(chunks)} TF-IDF embeddings ({dim} dimensions)")
    return chunks


# =========== Query embedding ===========

def get_query_embedding(query: str) -> List[float]:
    """Generate embedding for a search query."""
    if USE_OPENAI_EMBEDDINGS and OPENAI_API_KEY:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=OPENAI_API_KEY)
            response = client.embeddings.create(
                model="text-embedding-3-small",
                input=[query],
            )
            return response.data[0].embedding
        except Exception:
            return _get_tfidf_query_embedding(query)

    return _get_tfidf_query_embedding(query)


def _get_tfidf_query_embedding(query: str) -> List[float]:
    """Generate TF-IDF vector for a query using the corpus vocabulary."""
    global _idf_scores, _vocabulary

    if not _vocabulary:
        return _get_keyword_fallback(query)

    dim = len(_vocabulary)
    vocab_index = {term: i for i, term in enumerate(_vocabulary)}

    tokens = _tokenize(query)
    tf = Counter(tokens)
    total = len(tokens) if tokens else 1

    vector = [0.0] * dim
    for token, count in tf.items():
        if token in vocab_index:
            vector[vocab_index[token]] = (count / total) * _idf_scores.get(token, 1.0)

    return vector


def _get_keyword_fallback(query: str) -> List[float]:
    """Minimal keyword fallback when TF-IDF vocabulary is not available."""
    keywords = [
        "mig", "flux-cored", "tig", "stick", "polarity", "voltage", "amperage",
        "setup", "connect", "duty cycle", "output", "rating", "porosity",
        "spatter", "undercut", "wire feed", "arc", "troubleshoot", "safety",
        "torch", "electrode", "wire", "nozzle", "shielding gas", "ground clamp",
        "aluminum", "stainless", "steel", "thickness", "material",
    ]
    query_lower = query.lower()
    return [1.0 if kw in query_lower else 0.0 for kw in keywords]


# =========== BM25-style keyword scoring ===========

def bm25_score(query: str, text: str, k1: float = 1.5, b: float = 0.75, avgdl: float = 200.0) -> float:
    """
    BM25 scoring for keyword matching.
    
    Catches exact terms that semantic embeddings might miss
    (e.g., "OmniPro 220 model 57812" → exact match).
    """
    query_tokens = _tokenize(query)
    text_tokens = _tokenize(text)
    if not query_tokens or not text_tokens:
        return 0.0

    text_tf = Counter(text_tokens)
    dl = len(text_tokens)

    score = 0.0
    for qt in query_tokens:
        tf = text_tf.get(qt, 0)
        if tf > 0:
            # BM25 formula
            numerator = tf * (k1 + 1)
            denominator = tf + k1 * (1 - b + b * (dl / avgdl))
            score += numerator / denominator

    return score


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    try:
        a_arr = np.array(a, dtype=np.float32)
        b_arr = np.array(b, dtype=np.float32)

        dot_product = np.dot(a_arr, b_arr)
        norm_a = np.linalg.norm(a_arr)
        norm_b = np.linalg.norm(b_arr)

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return float(dot_product / (norm_a * norm_b))
    except Exception:
        return 0.0
