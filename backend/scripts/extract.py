"""
Knowledge extraction script.

Run once before starting the server:
  python scripts/extract.py

Processes all PDFs in files/ directory and builds the knowledge base:
1. Extracts text chunks from PDFs
2. Generates embeddings for semantic search
3. Uses Claude Vision to extract structured data (tables, specs)
4. Saves everything to backend/knowledge/data/

Output files created:
- backend/knowledge/data/chunks.json: Text chunks with embeddings
- backend/knowledge/data/image_catalog.json: Image metadata
- backend/knowledge/data/structured_data.json: Duty cycles, polarity, specs, troubleshooting
- backend/knowledge/data/images/: Extracted PNG images from PDFs
"""
import sys
from pathlib import Path

# Add backend to path so we can import our modules
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

import json
from knowledge.extractor import extract_all
from knowledge.vision_extractor import extract_structured_data
from knowledge.embeddings import generate_embeddings
from config import FILES_DIR, KNOWLEDGE_DIR


def main():
    """Main extraction pipeline."""
    print("\n" + "="*60)
    print("  OmniPro 220 Knowledge Base Extraction")
    print("="*60 + "\n")
    
    # Check if PDFs exist
    pdf_files = list(FILES_DIR.glob("*.pdf"))
    if not pdf_files:
        print(f"❌ Error: No PDF files found in {FILES_DIR}")
        print("   Please place PDF files in the 'files/' directory")
        return False
    
    print(f"📁 Found {len(pdf_files)} PDF files:")
    for pdf in pdf_files:
        print(f"   - {pdf.name}")
    print()
    
    try:
        # Step 1: Extract text and images from PDFs
        print("📄 STEP 1: Extracting text and images from PDFs...")
        print("-" * 60)
        result = extract_all()
        chunks = result["chunks"]
        images = result["images"]
        print(f"✓ Extracted {len(chunks)} text chunks")
        print(f"✓ Extracted {len(images)} images\n")
        
        # Step 2: Generate embeddings
        print("🔢 STEP 2: Generating embeddings for semantic search...")
        print("-" * 60)
        chunks_with_embeddings = generate_embeddings(chunks)
        print(f"✓ Generated embeddings for {len(chunks_with_embeddings)} chunks\n")
        
        # Step 3: Extract structured data using Claude Vision
        print("👁️ STEP 3: Extracting structured data with Claude Vision...")
        print("-" * 60)
        pdf_paths = [str(p) for p in pdf_files]
        structured_data = extract_structured_data(pdf_paths)
        print(f"✓ Extracted structured data\n")
        
        # Step 4: Save everything
        print("💾 STEP 4: Saving knowledge base...")
        print("-" * 60)
        
        chunks_file = KNOWLEDGE_DIR / "chunks.json"
        with open(chunks_file, "w") as f:
            json.dump(chunks_with_embeddings, f, indent=2)
        print(f"✓ Saved {chunks_file}")
        
        images_file = KNOWLEDGE_DIR / "image_catalog.json"
        with open(images_file, "w") as f:
            json.dump(images, f, indent=2)
        print(f"✓ Saved {images_file}")
        
        structured_file = KNOWLEDGE_DIR / "structured_data.json"
        with open(structured_file, "w") as f:
            json.dump(structured_data, f, indent=2)
        print(f"✓ Saved {structured_file}")
        
        print()
        print("="*60)
        print("✅ EXTRACTION COMPLETE!")
        print("="*60)
        print(f"\nKnowledge base stats:")
        print(f"  - {len(chunks_with_embeddings)} text chunks")
        print(f"  - {len(images)} images")
        print(f"  - Duty cycles: {list(structured_data.get('duty_cycles', {}).keys())}")
        print(f"  - Processes: {list(structured_data.get('polarity', {}).keys())}")
        print(f"\n💡 Next step: Run the backend with 'python backend/app.py'\n")
        
        return True
    
    except Exception as e:
        print(f"\n❌ Error during extraction: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
