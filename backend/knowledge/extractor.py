"""
Knowledge extraction layer - reads PDFs and extracts text, images, and structured data.

This module performs pure PDF processing:
1. Opens each PDF file
2. Extracts text by page with section headers
3. Extracts images and saves to disk
4. Detects table-containing pages
5. Returns structured data for storage

Does NOT call any AI - pure text/image extraction.
"""
import json
import io
import base64
from pathlib import Path
from typing import Dict, List, Tuple
import fitz  # PyMuPDF
from PIL import Image
from config import FILES_DIR, KNOWLEDGE_DIR, IMAGES_DIR


def extract_all() -> Dict:
    """
    Main entry point: Extract all PDFs in files/ directory.
    
    Returns:
        {"chunks": [...], "images": [...]}
    """
    print("📄 Extracting from PDFs...")
    
    pdf_files = list(FILES_DIR.glob("*.pdf"))
    if not pdf_files:
        print("⚠️ No PDF files found in", FILES_DIR)
        return {"chunks": [], "images": []}
    
    all_chunks = []
    all_images = []
    
    for pdf_path in pdf_files:
        print(f"  Processing {pdf_path.name}...")
        chunks = extract_text_chunks(str(pdf_path))
        images = extract_images(str(pdf_path))
        
        # If PDF had pages with no text (image-only), extract text via Vision
        doc = fitz.open(str(pdf_path))
        extracted_pages = {c["page"] for c in chunks}
        for page_num, page in enumerate(doc):
            if page_num not in extracted_pages:
                # Image-only page — render and extract text with Claude Vision
                vision_chunk = extract_image_page_text(str(pdf_path), page_num)
                if vision_chunk:
                    all_chunks.append(vision_chunk)
        doc.close()
        
        all_chunks.extend(chunks)
        all_images.extend(images)
    
    print(f"✓ Extracted {len(all_chunks)} text chunks and {len(all_images)} images")
    return {"chunks": all_chunks, "images": all_images}


def extract_image_page_text(pdf_path: str, page_num: int) -> Dict:
    """
    Extract text from an image-only PDF page using Claude Vision.
    
    Renders the page at high DPI and sends to Claude for OCR/description.
    """
    try:
        from anthropic import Anthropic
        from config import ANTHROPIC_API_KEY, MODEL
        
        doc = fitz.open(pdf_path)
        page = doc[page_num]
        source_name = Path(pdf_path).name
        
        # Render page at 200 DPI
        pix = page.get_pixmap(matrix=fitz.Matrix(200/72, 200/72))
        png_bytes = pix.tobytes("png")
        doc.close()
        
        # Also save the rendered page as an image
        img_filename = f"{source_name.replace('.pdf', '')}_p{page_num}_full.png"
        img_path = IMAGES_DIR / img_filename
        with open(img_path, "wb") as f:
            f.write(png_bytes)
        
        # Send to Claude Vision for text extraction
        client = Anthropic(api_key=ANTHROPIC_API_KEY)
        image_b64 = base64.standard_b64encode(png_bytes).decode("utf-8")
        
        response = client.messages.create(
            model=MODEL,
            max_tokens=4000,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": "image/png", "data": image_b64}
                    },
                    {
                        "type": "text",
                        "text": (
                            "This is a page from a Vulcan OmniPro 220 welding machine manual. "
                            "Extract ALL text and data visible on this page. Include every number, "
                            "label, table entry, and note. Format tables as structured text. "
                            "Be thorough — this data will be used for a knowledge base."
                        )
                    }
                ]
            }]
        )
        
        extracted_text = response.content[0].text.strip()
        if extracted_text:
            print(f"    ✓ Vision-extracted text from {source_name} page {page_num} ({len(extracted_text)} chars)")
            return {
                "id": f"{source_name.replace('.pdf', '')}_{page_num}",
                "source": source_name,
                "page": page_num,
                "section": f"Vision-extracted: {source_name}",
                "text": extracted_text,
                "has_table": True
            }
        return None
    except Exception as e:
        print(f"    ⚠️ Vision extraction failed for page {page_num}: {e}")
        return None


def extract_text_chunks(pdf_path: str) -> List[Dict]:
    """
    Extract text from PDF, split by page, detect section headers.
    
    Each chunk includes:
    - id: unique identifier
    - source: filename
    - page: page number (0-indexed)
    - section: detected section header
    - text: page text content
    - has_table: heuristic - are there lots of numbers/tables?
    """
    chunks = []
    doc = fitz.open(pdf_path)
    source_name = Path(pdf_path).name
    
    for page_num, page in enumerate(doc):
        # Extract text
        text = page.get_text()
        
        if not text.strip():
            continue
        
        # Detect section header (heuristic: first bold text or first heading)
        section = detect_section_header(page)
        
        # Detect if page likely contains a table
        has_table = detect_table_heuristic(text)
        
        chunk = {
            "id": f"{source_name.replace('.pdf', '')}_{page_num}",
            "source": source_name,
            "page": page_num,
            "section": section,
            "text": text.strip(),
            "has_table": has_table
        }
        chunks.append(chunk)
    
    doc.close()
    return chunks


def extract_images(pdf_path: str) -> List[Dict]:
    """
    Extract all images from PDF pages and save to disk.
    
    Each image includes:
    - id: unique identifier
    - source: filename
    - page: page number
    - filename: saved filename in images/
    - size_bytes: file size
    - context: surrounding text (used for auto-tagging)
    - tags: auto-detected tags based on context
    """
    images = []
    doc = fitz.open(pdf_path)
    source_name = Path(pdf_path).name
    source_base = source_name.replace(".pdf", "")
    
    for page_num, page in enumerate(doc):
        page_text = page.get_text()
        
        # Extract all images on the page
        image_list = page.get_images()
        
        for image_index, img_id in enumerate(image_list):
            try:
                # Get image data
                xref = img_id[0]
                pix = fitz.Pixmap(doc, xref)
                
                # Skip very small images (probably icons)
                if pix.width < 100 or pix.height < 100:
                    continue
                
                # Convert to PNG and save
                if pix.n - pix.alpha < 4:  # GRAY or RGB
                    pix = fitz.Pixmap(fitz.csRGB, pix)
                
                img_filename = f"{source_base}_p{page_num}_img{image_index}.png"
                img_path = IMAGES_DIR / img_filename
                pix.save(str(img_path))
                
                # Get file size
                size_bytes = img_path.stat().st_size
                
                # Auto-tag based on context
                tags = auto_tag_image(page_text)
                
                image = {
                    "id": f"{source_base}_p{page_num}_img{image_index}",
                    "source": source_name,
                    "page": page_num,
                    "filename": img_filename,
                    "size_bytes": size_bytes,
                    "context": page_text[:500],  # First 500 chars of page text
                    "tags": tags
                }
                images.append(image)
                
            except Exception as e:
                print(f"    ⚠️ Error extracting image: {e}")
                continue
    
    doc.close()
    return images


def detect_section_header(page) -> str:
    """
    Heuristic to detect section header from a PDF page.
    
    Looks for the largest or boldest text, or first text block.
    """
    try:
        page_text = page.get_text()
        lines = page_text.split('\n')
        
        # Find first non-empty line
        for line in lines:
            stripped = line.strip()
            if stripped and len(stripped) > 3:
                return stripped[:100]  # First 100 chars
        
        return "Section Unknown"
    except:
        return "Section Unknown"


def detect_table_heuristic(text: str) -> bool:
    """
    Heuristic: does this text block contain a table?
    
    Check for high frequency of pipes (|), dashes, or multiple spaces.
    """
    pipe_count = text.count('|')
    dash_count = text.count('-')
    
    # If lots of pipes or many dashes, likely a table
    return pipe_count > 5 or dash_count > 20


def auto_tag_image(surrounding_text: str) -> List[str]:
    """
    Auto-tag image based on surrounding text keywords.
    
    Returns list of tags from predefined categories.
    """
    text_lower = surrounding_text.lower()
    
    tag_keywords = {
        "wiring": ["wiring", "wire", "terminal", "connection", "socket", "cable"],
        "diagram": ["diagram", "schematic", "circuit", "flow"],
        "polarity": ["dcep", "dcen", "electrode", "polarity", "positive", "negative"],
        "duty_cycle": ["duty cycle", "amperage", "voltage", "output"],
        "front_panel": ["front", "panel", "control", "dial", "button", "switch"],
        "wire_feed": ["wire feed", "feed", "mechanism", "tensioner", "drive"],
        "weld_diagnosis": ["weld", "porosity", "spatter", "diagnosis", "defect"],
        "troubleshooting": ["troubleshooting", "problem", "issue", "fix"],
        "parts": ["parts", "component", "assembly", "identification"],
        "safety": ["safety", "warning", "danger", "caution"]
    }
    
    tags = []
    for tag, keywords in tag_keywords.items():
        if any(kw in text_lower for kw in keywords):
            tags.append(tag)
    
    return tags if tags else ["general"]
