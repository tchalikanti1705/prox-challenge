"""
Knowledge layer - extracts and stores information from manuals.
"""
from knowledge.extractor import extract_all
from knowledge.vision_extractor import extract_structured_data
from knowledge.embeddings import generate_embeddings
from knowledge.store import store

__all__ = ["extract_all", "extract_structured_data", "generate_embeddings", "store"]
