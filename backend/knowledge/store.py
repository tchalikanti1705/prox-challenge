"""
Knowledge store - singleton that loads and serves all knowledge base data.

Loaded once at server startup, stays in memory.
All tools read from this store.
"""
import json
from pathlib import Path
from typing import Dict, List, Optional
from knowledge.embeddings import get_query_embedding, cosine_similarity
from config import KNOWLEDGE_DIR


class KnowledgeStore:
    """
    Singleton data store for the OmniPro 220 knowledge base.
    
    Loads JSON files once at startup, provides query interface.
    """
    
    def __init__(self):
        self.chunks: List[Dict] = []           # Text chunks + embeddings
        self.structured_data: Dict = {}         # Tables, specs, duty cycles
        self.image_catalog: List[Dict] = []     # Image metadata
        self.is_loaded: bool = False
    
    def load(self):
        """
        Load all JSON files from knowledge/data/.
        
        Call once at server startup.
        """
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
            
            self.is_loaded = True
            print("✓ Knowledge base ready")
        
        except Exception as e:
            print(f"❌ Error loading knowledge base: {e}")
            self.is_loaded = False
    
    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        Semantic search: find most relevant text chunks.
        
        Uses embedding similarity if available.
        
        Args:
            query: Search query
            top_k: Number of results to return
        
        Returns:
            List of chunks sorted by similarity, each with:
            - page, section, text, score
        """
        if not self.chunks:
            return []
        
        try:
            # Get query embedding
            query_embedding = get_query_embedding(query)
            
            # Calculate similarity with all chunks
            results = []
            for chunk in self.chunks:
                if "embedding" in chunk:
                    sim = cosine_similarity(query_embedding, chunk["embedding"])
                else:
                    sim = simple_text_match(query, chunk["text"])
                
                results.append({
                    "page": chunk.get("page", 0),
                    "section": chunk.get("section", "Unknown"),
                    "source": chunk.get("source", "Unknown"),
                    "text": chunk["text"],
                    "score": sim
                })
            
            # Sort by score and return top_k
            results.sort(key=lambda x: x["score"], reverse=True)
            return results[:top_k]
        
        except Exception as e:
            print(f"⚠️ Search error: {e}")
            return []
    
    def get_duty_cycle(self, process: str, voltage: str, amperage: Optional[str] = None) -> Dict:
        """
        Exact lookup in duty cycle table.
        
        Args:
            process: MIG, Flux-Cored, TIG, or Stick
            voltage: 120V or 240V
            amperage: Optional specific amperage (e.g. "200A")
        
        Returns:
            {
                "process": "MIG",
                "voltage": "240V",
                "amperage": "200A",
                "duty_cycle": 30,
                "all_ratings": {...}
            }
        """
        duty_cycles = self.structured_data.get("duty_cycles", {})
        
        if process not in duty_cycles:
            return {"error": f"Process '{process}' not found"}
        
        process_data = duty_cycles[process]
        
        if voltage not in process_data:
            return {"error": f"Voltage '{voltage}' not available for {process}"}
        
        amperage_data = process_data[voltage]
        
        result = {
            "process": process,
            "voltage": voltage,
            "all_ratings": amperage_data
        }
        
        if amperage:
            if amperage in amperage_data:
                result["amperage"] = amperage
                result["duty_cycle"] = amperage_data[amperage]
            else:
                result["error"] = f"Amperage '{amperage}' not available"
                result["available_amperages"] = list(amperage_data.keys())
        
        return result
    
    def get_polarity(self, process: str) -> Dict:
        """
        Lookup polarity and socket connections for a process.
        
        Args:
            process: MIG, Flux-Cored, TIG, or Stick
        
        Returns:
            {
                "process": "TIG",
                "type": "DCEN",
                "torch_socket": "negative",
                "ground_socket": "positive",
                "notes": "..."
            }
        """
        polarity_data = self.structured_data.get("polarity", {})
        
        if process not in polarity_data:
            return {"error": f"Process '{process}' not found"}
        
        data = polarity_data[process]
        data["process"] = process
        return data
    
    def get_troubleshooting(self, symptom: str) -> Dict:
        """
        Find troubleshooting guidance for a symptom.
        
        Uses fuzzy matching: checks if any word in the symptom matches
        the problem name or any keyword in causes/fixes.
        """
        troubleshooting = self.structured_data.get("troubleshooting", [])
        
        symptom_lower = symptom.lower()
        symptom_words = set(symptom_lower.split())
        
        # First pass: exact substring match on problem name
        for issue in troubleshooting:
            if symptom_lower in issue.get("problem", "").lower():
                return issue
        
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
            return best_match
        
        # Third pass: search in text chunks for troubleshooting content
        search_results = self.search(f"troubleshooting {symptom}", top_k=3)
        if search_results:
            return {
                "problem": symptom,
                "from_manual_search": True,
                "relevant_sections": [
                    {"page": r["page"], "section": r["section"], "text": r["text"][:300]}
                    for r in search_results
                ]
            }
        
        return {"error": f"No troubleshooting data found for '{symptom}'"}
        
        return {"error": f"No troubleshooting data found for '{symptom}'"}
    
    def search_images(self, query: str = "", tags: List[str] = None) -> List[Dict]:
        """
        Find relevant images by keyword or tags.
        
        Args:
            query: Text search in image descriptions/context
            tags: Filter by tags (wiring, polarity, duty_cycle, etc.)
        
        Returns:
            List of image metadata
        """
        if tags is None:
            tags = []
        
        results = []
        query_lower = query.lower()
        
        for image in self.image_catalog:
            # Check text match
            text_match = (
                query_lower in image.get("filename", "").lower() or
                query_lower in image.get("context", "").lower() or
                any(kw in query_lower for kw in image.get("tags", []))
            )
            
            # Check tag match
            tag_match = not tags or any(t in image.get("tags", []) for t in tags)
            
            if text_match and tag_match:
                results.append({
                    "id": image.get("id"),
                    "source": image.get("source"),
                    "page": image.get("page"),
                    "filename": image.get("filename"),
                    "tags": image.get("tags", []),
                    "context": image.get("context", "")[:200]
                })
        
        return results
    
    def get_image_path(self, image_id: str) -> Optional[Path]:
        """
        Get filesystem path for a specific image.
        
        Args:
            image_id: Image ID
        
        Returns:
            Path to image file or None if not found
        """
        for image in self.image_catalog:
            if image.get("id") == image_id:
                img_path = KNOWLEDGE_DIR / "images" / image.get("filename")
                if img_path.exists():
                    return img_path
        
        return None
    
    def get_specs(self) -> Dict:
        """
        Get all machine specifications.
        
        Returns:
            Dict with input_voltage, processes, max_output, wire_sizes, etc.
        """
        return self.structured_data.get("specifications", {})


def simple_text_match(query: str, text: str) -> float:
    """
    Simple text matching when embeddings aren't available.
    
    Scores based on keyword presence and frequency.
    """
    query_lower = query.lower()
    text_lower = text.lower()
    
    # Count keyword matches
    score = 0.0
    words = query_lower.split()
    
    for word in words:
        if len(word) > 2:  # Skip small words
            count = text_lower.count(word)
            score += min(count, 5) * 0.1  # Cap contribution per word
    
    return min(score, 1.0)


# Global singleton instance
store = KnowledgeStore()
