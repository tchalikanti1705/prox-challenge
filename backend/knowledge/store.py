"""
Knowledge store - singleton that loads and serves all knowledge base data.

Loaded once at server startup, stays in memory.
All tools read from this store.

Improvements over v1:
- Hybrid search: embedding similarity + BM25 keyword + structured match
- Pre-computed numpy search index for O(1) batch similarity
- Rebuilds TF-IDF vocabulary on load (no re-extraction needed)
- Cleans troubleshooting entries with missing problem names
- Duty cycle interpolation for in-between amperages
- Manual page references on all results
"""
import json
import re
from pathlib import Path
from typing import Dict, List, Optional
from knowledge.embeddings import (
    get_query_embedding, cosine_similarity,
    batch_cosine_similarity, build_search_index,
    rebuild_tfidf_vocabulary, bm25_score,
)
from config import (
    KNOWLEDGE_DIR,
    SEARCH_WEIGHT_EMBEDDING, SEARCH_WEIGHT_KEYWORD, SEARCH_WEIGHT_STRUCTURED,
)


class KnowledgeStore:
    """
    Singleton data store for the OmniPro 220 knowledge base.
    
    Loads JSON files once at startup, provides query interface.
    """
    
    def __init__(self):
        self.chunks: List[Dict] = []
        self.structured_data: Dict = {}
        self.image_catalog: List[Dict] = []
        self.is_loaded: bool = False
        self._avg_chunk_len: float = 200.0  # For BM25 normalization
    
    def load(self):
        """Load all JSON files from knowledge/data/. Call once at startup."""
        print("📚 Loading knowledge base...")
        
        try:
            # Load chunks
            chunks_path = KNOWLEDGE_DIR / "chunks.json"
            if chunks_path.exists():
                with open(chunks_path) as f:
                    self.chunks = json.load(f)
                print(f"  ✓ Loaded {len(self.chunks)} text chunks")
            
            # Load structured data
            structured_path = KNOWLEDGE_DIR / "structured_data.json"
            if structured_path.exists():
                with open(structured_path) as f:
                    self.structured_data = json.load(f)
                print(f"  ✓ Loaded structured data")
            
            # Load image catalog
            images_path = KNOWLEDGE_DIR / "image_catalog.json"
            if images_path.exists():
                with open(images_path) as f:
                    self.image_catalog = json.load(f)
                print(f"  ✓ Loaded {len(self.image_catalog)} image references")
            
            # === Post-load enhancements ===
            
            # Clean troubleshooting: remove entries with no problem name
            self._clean_troubleshooting()
            
            # Compute average chunk length for BM25
            if self.chunks:
                self._avg_chunk_len = sum(len(c.get("text", "")) for c in self.chunks) / len(self.chunks)
            
            # Rebuild TF-IDF vocabulary from loaded chunks
            if self.chunks:
                rebuild_tfidf_vocabulary(self.chunks)
            
            # Pre-compute search index (normalized embedding matrix)
            if self.chunks:
                build_search_index(self.chunks)
            
            self.is_loaded = True
            print("✓ Knowledge base ready")
        
        except Exception as e:
            print(f"❌ Error loading knowledge base: {e}")
            self.is_loaded = False
    
    def _clean_troubleshooting(self):
        """Remove troubleshooting entries with missing or None problem names."""
        ts = self.structured_data.get("troubleshooting", [])
        before = len(ts)
        cleaned = [
            t for t in ts
            if t.get("problem") and (t.get("causes") or t.get("fixes"))
        ]
        self.structured_data["troubleshooting"] = cleaned
        removed = before - len(cleaned)
        if removed:
            print(f"  ✓ Cleaned troubleshooting: removed {removed} incomplete entries ({len(cleaned)} remaining)")
    
    # ============================================================
    #  HYBRID SEARCH
    # ============================================================
    
    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        Hybrid search: embedding similarity + BM25 keyword + structured match.
        
        Weights (from config):
          - 50% embedding similarity (semantic meaning)
          - 30% BM25 keyword score (exact terms)
          - 20% structured data bonus (duty cycle, polarity, specs mentions)
        
        Returns list of chunks sorted by combined score.
        """
        if not self.chunks:
            return []
        
        try:
            # Score 1: Embedding similarity (batch, vectorized)
            query_embedding = get_query_embedding(query)
            embedding_scores = batch_cosine_similarity(query_embedding)
            
            # If batch method returns empty (no matrix), fall back to individual
            if len(embedding_scores) == 0:
                embedding_scores = []
                for chunk in self.chunks:
                    if "embedding" in chunk:
                        sim = cosine_similarity(query_embedding, chunk["embedding"])
                    else:
                        sim = _simple_text_match(query, chunk["text"])
                    embedding_scores.append(sim)
                embedding_scores = __import__('numpy').array(embedding_scores)
            
            # Score 2: BM25 keyword matching
            keyword_scores = []
            for chunk in self.chunks:
                score = bm25_score(query, chunk["text"], avgdl=self._avg_chunk_len)
                keyword_scores.append(score)
            
            # Normalize BM25 scores to 0-1 range
            max_kw = max(keyword_scores) if keyword_scores else 1.0
            if max_kw > 0:
                keyword_scores = [s / max_kw for s in keyword_scores]
            
            # Score 3: Structured data bonus
            structured_bonus = self._structured_match_score(query)
            
            # Combine with configurable weights
            results = []
            for i, chunk in enumerate(self.chunks):
                emb_score = float(embedding_scores[i]) if i < len(embedding_scores) else 0.0
                kw_score = keyword_scores[i] if i < len(keyword_scores) else 0.0
                struct_score = structured_bonus.get(i, 0.0)
                
                combined = (
                    SEARCH_WEIGHT_EMBEDDING * emb_score +
                    SEARCH_WEIGHT_KEYWORD * kw_score +
                    SEARCH_WEIGHT_STRUCTURED * struct_score
                )
                
                results.append({
                    "page": chunk.get("page", 0),
                    "section": chunk.get("section", "Unknown"),
                    "source": chunk.get("source", "Unknown"),
                    "text": chunk["text"],
                    "score": combined,
                    "manual_reference": f"Owner's manual, page {chunk.get('page', '?')}",
                })
            
            results.sort(key=lambda x: x["score"], reverse=True)
            return results[:top_k]
        
        except Exception as e:
            print(f"⚠️ Search error: {e}")
            return []
    
    def _structured_match_score(self, query: str) -> Dict[int, float]:
        """
        Check if query relates to structured data (duty cycle, polarity, specs).
        Returns dict of chunk_index → bonus_score.
        """
        query_lower = query.lower()
        bonuses: Dict[int, float] = {}
        
        # Detect structured data intent
        is_duty_cycle = any(w in query_lower for w in ["duty cycle", "amperage", "how long", "continuous", "rating"])
        is_polarity = any(w in query_lower for w in ["polarity", "socket", "terminal", "dcen", "dcep", "connect", "cable"])
        is_specs = any(w in query_lower for w in ["specification", "specs", "weight", "dimension", "input voltage", "max output"])
        is_troubleshoot = any(w in query_lower for w in ["problem", "issue", "porosity", "spatter", "troubleshoot", "fix", "cause"])
        
        # Detect process
        process_match = None
        for proc in ["mig", "tig", "stick", "flux"]:
            if proc in query_lower:
                process_match = proc
                break
        
        # Boost chunks that overlap with structured data topics
        for i, chunk in enumerate(self.chunks):
            text_lower = chunk.get("text", "").lower()
            section = chunk.get("section", "").lower()
            bonus = 0.0
            
            if is_duty_cycle and any(w in text_lower for w in ["duty cycle", "amperage", "rating"]):
                bonus += 0.5
            if is_polarity and any(w in text_lower for w in ["polarity", "dcen", "dcep", "terminal", "socket"]):
                bonus += 0.5
            if is_specs and any(w in text_lower for w in ["specification", "input voltage", "output"]):
                bonus += 0.5
            if is_troubleshoot and any(w in text_lower for w in ["troubleshoot", "problem", "cause", "fix"]):
                bonus += 0.4
            if process_match and process_match in text_lower:
                bonus += 0.2
            
            if bonus > 0:
                bonuses[i] = min(bonus, 1.0)
        
        return bonuses
    
    # ============================================================
    #  DUTY CYCLE (with interpolation)
    # ============================================================
    
    def get_duty_cycle(self, process: str, voltage: str, amperage: Optional[str] = None) -> Dict:
        """
        Exact lookup in duty cycle table with interpolation for in-between values.
        """
        duty_cycles = self.structured_data.get("duty_cycles", {})
        
        if process not in duty_cycles:
            return {"error": f"Process '{process}' not found", "available": list(duty_cycles.keys())}
        
        process_data = duty_cycles[process]
        
        if voltage not in process_data:
            return {"error": f"Voltage '{voltage}' not available for {process}", "available": list(process_data.keys())}
        
        amperage_data = process_data[voltage]
        
        result = {
            "process": process,
            "voltage": voltage,
            "all_ratings": amperage_data,
            "manual_reference": "Owner's manual, duty cycle rating table",
        }
        
        if amperage:
            if amperage in amperage_data:
                result["amperage"] = amperage
                result["duty_cycle"] = amperage_data[amperage]
            else:
                # Try interpolation
                interpolated = self._interpolate_duty_cycle(amperage_data, amperage)
                if interpolated is not None:
                    result["amperage"] = amperage
                    result["duty_cycle"] = interpolated
                    result["interpolated"] = True
                    result["note"] = "This value is interpolated between known ratings. Actual duty cycle may vary."
                else:
                    result["error"] = f"Amperage '{amperage}' not available"
                    result["available_amperages"] = list(amperage_data.keys())
        
        return result
    
    def _interpolate_duty_cycle(self, amperage_data: Dict, target_amperage: str) -> Optional[float]:
        """
        Linear interpolation between known duty cycle data points.
        
        e.g., if 115A=100% and 200A=25%, then 150A ≈ 56%
        """
        # Parse target amperage
        target_num = _parse_amperage(target_amperage)
        if target_num is None:
            return None
        
        # Parse all known data points
        known_points = []
        for amp_str, dc_val in amperage_data.items():
            amp_num = _parse_amperage(amp_str)
            if amp_num is not None and isinstance(dc_val, (int, float)):
                known_points.append((amp_num, dc_val))
        
        if len(known_points) < 2:
            return None
        
        known_points.sort(key=lambda x: x[0])
        
        # Check bounds
        if target_num < known_points[0][0] or target_num > known_points[-1][0]:
            return None
        
        # Find bracketing points
        for i in range(len(known_points) - 1):
            a1, dc1 = known_points[i]
            a2, dc2 = known_points[i + 1]
            if a1 <= target_num <= a2:
                if a2 == a1:
                    return dc1
                ratio = (target_num - a1) / (a2 - a1)
                return round(dc1 + ratio * (dc2 - dc1), 1)
        
        return None
    
    # ============================================================
    #  POLARITY
    # ============================================================
    
    def get_polarity(self, process: str) -> Dict:
        """Lookup polarity and socket connections for a process."""
        polarity_data = self.structured_data.get("polarity", {})
        
        if process not in polarity_data:
            return {"error": f"Process '{process}' not found", "available": list(polarity_data.keys())}
        
        data = dict(polarity_data[process])  # Copy to avoid mutating
        data["process"] = process
        data["manual_reference"] = f"Owner's manual, {process} polarity setup"
        return data
    
    # ============================================================
    #  TROUBLESHOOTING
    # ============================================================
    
    def get_troubleshooting(self, symptom: str) -> Dict:
        """
        Find troubleshooting guidance for a symptom.
        Uses fuzzy matching against cleaned troubleshooting data.
        """
        troubleshooting = self.structured_data.get("troubleshooting", [])
        
        symptom_lower = symptom.lower()
        symptom_words = set(symptom_lower.split())
        
        # First pass: exact substring match on problem name
        for issue in troubleshooting:
            if symptom_lower in issue.get("problem", "").lower():
                result = dict(issue)
                result["manual_reference"] = "Owner's manual, troubleshooting section"
                return result
        
        # Second pass: word overlap with problem, causes, fixes
        best_match = None
        best_score = 0
        for issue in troubleshooting:
            score = 0
            problem = issue.get("problem", "").lower()
            causes_text = " ".join(issue.get("causes", [])).lower()
            fixes_text = " ".join(issue.get("fixes", [])).lower()
            all_text = f"{problem} {causes_text} {fixes_text}"
            
            for word in symptom_words:
                if len(word) > 2 and word in all_text:
                    score += 1
            
            if score > best_score:
                best_score = score
                best_match = issue
        
        if best_match and best_score >= 1:
            result = dict(best_match)
            result["manual_reference"] = "Owner's manual, troubleshooting section"
            return result
        
        # Third pass: search in text chunks for troubleshooting content
        search_results = self.search(f"troubleshooting {symptom}", top_k=3)
        if search_results:
            return {
                "problem": symptom,
                "from_manual_search": True,
                "manual_reference": "Owner's manual, troubleshooting section",
                "relevant_sections": [
                    {"page": r["page"], "section": r["section"], "text": r["text"][:300]}
                    for r in search_results
                ]
            }
        
        return {"error": f"No troubleshooting data found for '{symptom}'"}
    
    # ============================================================
    #  IMAGES
    # ============================================================
    
    def search_images(self, query: str = "", tags: List[str] = None) -> List[Dict]:
        """Find relevant images by keyword or tags."""
        if tags is None:
            tags = []
        
        results = []
        query_lower = query.lower()
        
        for image in self.image_catalog:
            text_match = (
                query_lower in image.get("filename", "").lower() or
                query_lower in image.get("context", "").lower() or
                any(kw in query_lower for kw in image.get("tags", []))
            )
            
            tag_match = not tags or any(t in image.get("tags", []) for t in tags)
            
            if text_match and tag_match:
                results.append({
                    "id": image.get("id"),
                    "source": image.get("source"),
                    "page": image.get("page"),
                    "filename": image.get("filename"),
                    "tags": image.get("tags", []),
                    "context": image.get("context", "")[:200],
                    "manual_reference": f"Owner's manual, page {image.get('page', '?')}",
                })
        
        return results
    
    def get_image_path(self, image_id: str) -> Optional[Path]:
        """Get filesystem path for a specific image."""
        for image in self.image_catalog:
            if image.get("id") == image_id:
                img_path = KNOWLEDGE_DIR / "images" / image.get("filename")
                if img_path.exists():
                    return img_path
        return None
    
    # ============================================================
    #  SPECIFICATIONS
    # ============================================================
    
    def get_specs(self) -> Dict:
        """Get all machine specifications."""
        specs = self.structured_data.get("specifications", {})
        if specs:
            specs["manual_reference"] = "Owner's manual, specifications section"
        return specs


# =========== Helpers ===========

def _parse_amperage(amp_str: str) -> Optional[float]:
    """Parse '200A' or '200' into a number."""
    match = re.search(r'(\d+\.?\d*)', str(amp_str))
    if match:
        return float(match.group(1))
    return None


def _simple_text_match(query: str, text: str) -> float:
    """Simple text matching fallback."""
    query_lower = query.lower()
    text_lower = text.lower()
    score = 0.0
    for word in query_lower.split():
        if len(word) > 2:
            count = text_lower.count(word)
            score += min(count, 5) * 0.1
    return min(score, 1.0)


# Global singleton instance
store = KnowledgeStore()
