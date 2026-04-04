"""
Embeddings layer - generates vector embeddings for semantic search.

Can use:
1. OpenAI embeddings (text-embedding-3-small) - requires OPENAI_API_KEY
2. TF-IDF embeddings - no external API needed, significantly better than keyword matching
"""
import json
import math
import re
from collections import Counter
import numpy as np
from typing import List, Dict
from config import USE_OPENAI_EMBEDDINGS


# Module-level TF-IDF state (populated during generate_embeddings)
_idf_scores: Dict[str, float] = {}
_vocabulary: List[str] = []


def _tokenize(text: str) -> List[str]:
    """Tokenize text into lowercase words, removing short/stop words."""
    stop_words = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "shall", "can", "need", "must", "and", "or",
        "but", "if", "then", "than", "that", "this", "these", "those", "it",
        "its", "of", "in", "on", "at", "to", "for", "with", "by", "from",
        "as", "into", "about", "not", "no", "so", "up", "out", "all", "also",
        "each", "any", "when", "what", "which", "who", "how", "where", "there",
        "here", "more", "some", "only", "very", "just", "one", "two", "see",
    }
    words = re.findall(r'[a-z][a-z0-9\-]{1,}', text.lower())
    return [w for w in words if w not in stop_words]


def _build_tfidf_vocabulary(chunks: List[Dict], max_features: int = 500) -> tuple:
    """Build TF-IDF vocabulary from corpus. Returns (vocabulary, idf_scores)."""
    n_docs = len(chunks)
    doc_freq = Counter()

    # Count document frequency for each term
    for chunk in chunks:
        tokens = set(_tokenize(chunk["text"]))
        for token in tokens:
            doc_freq[token] += 1

    # Keep top max_features by document frequency (but filter out terms in >90% of docs)
    filtered = {
        term: count for term, count in doc_freq.items()
        if count >= 2 and count < n_docs * 0.9
    }
    vocab = sorted(filtered, key=lambda t: filtered[t], reverse=True)[:max_features]

    # Compute IDF: log(N / df) + 1  (smoothed)
    idf = {term: math.log(n_docs / (filtered[term] + 1)) + 1 for term in vocab}

    return vocab, idf


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
        import os

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("  ⚠️ OPENAI_API_KEY not set, falling back to TF-IDF")
            return generate_with_tfidf(chunks)

        client = OpenAI(api_key=api_key)
        texts = [chunk["text"][:8191] for chunk in chunks]

        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=texts,
        )

        for chunk, embedding_obj in zip(chunks, response.data):
            chunk["embedding"] = embedding_obj.embedding

        print(f"  ✓ Generated {len(chunks)} embeddings via OpenAI")
        return chunks
    except Exception as e:
        print(f"  ⚠️ OpenAI embedding failed: {e}, falling back to TF-IDF")
        return generate_with_tfidf(chunks)


def generate_with_tfidf(chunks: List[Dict]) -> List[Dict]:
    """
    Generate TF-IDF embeddings (no external API needed).

    Builds a vocabulary from the corpus, computes TF-IDF vectors per chunk.
    Much more expressive than binary keyword matching.
    """
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
                # TF (normalized) * IDF
                vector[vocab_index[token]] = (count / total) * _idf_scores.get(token, 1.0)

        chunk["embedding"] = vector

    print(f"  ✓ Generated {len(chunks)} TF-IDF embeddings ({dim} dimensions)")
    return chunks


def get_query_embedding(query: str) -> List[float]:
    """Generate embedding for a search query."""
    if USE_OPENAI_EMBEDDINGS:
        try:
            from openai import OpenAI
            import os

            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                return _get_tfidf_query_embedding(query)

            client = OpenAI(api_key=api_key)
            response = client.embeddings.create(
                model="text-embedding-3-small",
                input=[query],
            )
            return response.data[0].embedding
        except:
            return _get_tfidf_query_embedding(query)
    else:
        return _get_tfidf_query_embedding(query)


def _get_tfidf_query_embedding(query: str) -> List[float]:
    """Generate TF-IDF vector for a query using the corpus vocabulary."""
    global _idf_scores, _vocabulary

    if not _vocabulary:
        # Vocabulary not yet built — will happen if server restarts
        # without re-extraction. Use keyword fallback.
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


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """
    Calculate cosine similarity between two vectors.
    
    Returns value between 0 and 1, where 1 is identical.
    """
    try:
        a_arr = np.array(a, dtype=np.float32)
        b_arr = np.array(b, dtype=np.float32)
        
        dot_product = np.dot(a_arr, b_arr)
        norm_a = np.linalg.norm(a_arr)
        norm_b = np.linalg.norm(b_arr)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return float(dot_product / (norm_a * norm_b))
    except:
        return 0.0
