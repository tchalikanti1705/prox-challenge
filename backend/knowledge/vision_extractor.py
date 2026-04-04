"""
Vision extraction layer - uses Claude Vision API to read complex tables, diagrams, and specifications.

This module:
1. Renders PDF pages as high-resolution images
2. Sends to Claude Vision with targeted prompts
3. Extracts structured data (duty cycles, polarity, specs)
4. Returns clean JSON
"""
import json
import base64
import re
import io
from typing import Dict, List
from pathlib import Path
import fitz  # PyMuPDF
from anthropic import Anthropic
from config import ANTHROPIC_API_KEY, MODEL


def _parse_json_response(text: str) -> dict:
    """Parse JSON from Claude response, stripping markdown code fences if present."""
    text = text.strip()
    # Strip ```json ... ``` or ``` ... ``` wrappers
    m = re.match(r'^```(?:json)?\s*\n?(.*?)```\s*$', text, re.DOTALL)
    if m:
        text = m.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {}


def extract_structured_data(pdf_paths: List[str]) -> Dict:
    """
    Extract structured data (tables, specs) from PDFs using Claude Vision.
    
    Steps:
    1. Render each PDF page as image
    2. First pass: identify which pages have tables
    3. Second pass: extract structured data from table pages
    
    Returns complete structured_data.json content with:
    - duty_cycles: process -> voltage -> amperage -> percentage
    - polarity: process -> setup info
    - specifications: machine specs
    - troubleshooting: problems and solutions
    """
    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    
    print("👁️ Extracting structured data with Claude Vision...")
    
    # Render all pages as images
    page_images = []
    for pdf_path in pdf_paths:
        print(f"  Rendering pages from {Path(pdf_path).name}...")
        pages = render_pdf_pages_as_images(pdf_path, dpi=150)
        page_images.extend([(Path(pdf_path).name, i, img) for i, img in enumerate(pages)])
    
    print(f"  Rendered {len(page_images)} pages")
    
    # Process images with Claude Vision
    structured_data = {
        "duty_cycles": {},
        "polarity": {},
        "specifications": {},
        "troubleshooting": [],
        "extracted_at": "auto"
    }
    
    # Process all pages to find tables and structured data
    for filename, page_num, image_bytes in page_images:
        try:
            # Check if this page likely contains a table
            is_table_page = check_for_table(client, image_bytes, filename, page_num)
            
            if is_table_page:
                # Extract structured data from this page
                extracted = extract_from_table_page(client, image_bytes, filename, page_num)
                
                # Merge extracted data
                if extracted.get("duty_cycles"):
                    structured_data["duty_cycles"].update(extracted["duty_cycles"])
                if extracted.get("polarity"):
                    structured_data["polarity"].update(extracted["polarity"])
                if extracted.get("specifications"):
                    structured_data["specifications"].update(extracted["specifications"])
                if extracted.get("troubleshooting"):
                    structured_data["troubleshooting"].extend(extracted["troubleshooting"])
        
        except Exception as e:
            print(f"    ⚠️ Error processing {filename} page {page_num}: {e}")
    
    # Fallback: fill in missing sections from default data
    # Vision may not extract everything (e.g., polarity from wiring diagrams,
    # Flux-Cored data which shares MIG settings)
    defaults = get_default_vulcan_specs()

    # If Vision found no duty cycles at all, use defaults entirely
    if not structured_data["duty_cycles"]:
        structured_data = defaults
    else:
        # Clean up duty cycles: remove non-process keys like "120VAC", "240VAC"
        valid_processes = {"MIG", "Flux-Cored", "TIG", "Stick"}
        structured_data["duty_cycles"] = {
            k: v for k, v in structured_data["duty_cycles"].items()
            if k in valid_processes
        }
        # Fill in any missing processes from defaults
        for process, voltages in defaults["duty_cycles"].items():
            if process not in structured_data["duty_cycles"]:
                structured_data["duty_cycles"][process] = voltages
        
        # Fill missing polarity from defaults (Vision rarely extracts wiring diagrams)
        if not structured_data["polarity"]:
            structured_data["polarity"] = defaults["polarity"]
        else:
            for process, data in defaults["polarity"].items():
                if process not in structured_data["polarity"]:
                    structured_data["polarity"][process] = data
        
        # Fill missing specifications
        if not structured_data["specifications"]:
            structured_data["specifications"] = defaults["specifications"]
        
        # Merge troubleshooting: keep Vision results + add defaults for missing problems
        existing_problems = {
            t.get("problem", "").lower() for t in structured_data["troubleshooting"]
        }
        for entry in defaults["troubleshooting"]:
            if entry["problem"].lower() not in existing_problems:
                structured_data["troubleshooting"].append(entry)
        
        structured_data["extracted_at"] = "auto+defaults"
    
    print("✓ Structured data extracted")
    return structured_data


def render_pdf_pages_as_images(pdf_path: str, dpi: int = 150) -> List[bytes]:
    """
    Render PDF pages as PNG images at specified DPI.
    
    Returns list of PNG image bytes.
    """
    images = []
    doc = fitz.open(pdf_path)
    
    for page_num, page in enumerate(doc):
        # Render at higher DPI for better text recognition
        pix = page.get_pixmap(matrix=fitz.Matrix(dpi/72, dpi/72))
        
        # Convert to PNG bytes
        png_bytes = pix.tobytes("png")
        images.append(png_bytes)
    
    doc.close()
    return images


def check_for_table(client: Anthropic, image_bytes: bytes, filename: str, page_num: int) -> bool:
    """
    Quick check: does this page contain a table or specs?
    
    Uses Claude Vision to do a binary classification.
    """
    try:
        # Encode image to base64
        image_b64 = base64.standard_b64encode(image_bytes).decode("utf-8")
        
        response = client.messages.create(
            model=MODEL,
            max_tokens=100,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": image_b64
                            }
                        },
                        {
                            "type": "text",
                            "text": (
                                "Does this page contain a table, matrix, or structured data "
                                "(duty cycle table, specifications, wiring table, polarity setup, troubleshooting matrix)? "
                                "Answer with ONLY 'yes' or 'no'."
                            )
                        }
                    ]
                }
            ]
        )
        
        answer = response.content[0].text.lower().strip()
        return "yes" in answer
    
    except Exception as e:
        print(f"    ⚠️ Error checking for table: {e}")
        return False


def extract_from_table_page(client: Anthropic, image_bytes: bytes, filename: str, page_num: int) -> Dict:
    """
    Extract structured data from a table page using Claude Vision.
    
    Returns JSON with duty_cycles, polarity, specifications, or troubleshooting data.
    """
    try:
        # Encode image to base64
        image_b64 = base64.standard_b64encode(image_bytes).decode("utf-8")
        
        response = client.messages.create(
            model=MODEL,
            max_tokens=2000,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": image_b64
                            }
                        },
                        {
                            "type": "text",
                            "text": (
                                "Extract ALL structured data from this page. Return ONLY valid JSON with this structure:\n"
                                "{\n"
                                '  "duty_cycles": {"PROCESS": {"VOLTAGE": {"AMPERAGE": percentage}}},\n'
                                '  "polarity": {"PROCESS": {"type": "...", "torch_socket": "...", "ground_socket": "..."}},\n'
                                '  "specifications": {...},\n'
                                '  "troubleshooting": [...]\n'
                                "}\n"
                                "If section is not present, use empty object/array. "
                                "For duty cycles, PROCESS is MIG/Flux-Cored/TIG/Stick, "
                                "VOLTAGE is 120V/240V, AMPERAGE is the value like 90A, percentage is like 60. "
                                "Return ONLY the JSON, no other text."
                            )
                        }
                    ]
                }
            ]
        )
        
        result_text = response.content[0].text.strip()
        
        # Parse JSON, handling markdown code fences
        data = _parse_json_response(result_text)
        if not data:
            print(f"    ⚠️ Could not parse Claude response as JSON from {filename} p{page_num}")
        return data
    
    except Exception as e:
        print(f"    ⚠️ Error extracting data: {e}")
        return {}


def get_default_vulcan_specs() -> Dict:
    """
    Default Vulcan OmniPro 220 specifications.
    
    This is hardcoded data based on the manual.
    Used as fallback if vision extraction doesn't work.
    """
    return {
        "duty_cycles": {
            "MIG": {
                "240V": {
                    "90A": 60, "130A": 40, "200A": 30, "220A": 20
                },
                "120V": {
                    "30A": 60, "70A": 40, "90A": 30
                }
            },
            "Flux-Cored": {
                "240V": {
                    "90A": 60, "130A": 40, "150A": 35, "175A": 25
                }
            },
            "TIG": {
                "240V": {
                    "20A": 80, "40A": 60, "60A": 40, "80A": 25
                }
            },
            "Stick": {
                "240V": {
                    "40A": 80, "60A": 70, "90A": 50, "120A": 30
                }
            }
        },
        "polarity": {
            "MIG": {
                "type": "DCEP (Reverse Polarity)",
                "torch_socket": "positive",
                "ground_socket": "negative",
                "notes": "Electrode positive for standard MIG welding"
            },
            "Flux-Cored": {
                "type": "DCEP (Reverse Polarity)",
                "torch_socket": "positive",
                "ground_socket": "negative",
                "notes": "Most flux-cored wires use DCEP"
            },
            "TIG": {
                "type": "DCEN (Straight Polarity)",
                "torch_socket": "negative",
                "ground_socket": "positive",
                "notes": "DC electrode negative for standard TIG"
            },
            "Stick": {
                "type": "DCEP (Reverse Polarity)",
                "torch_socket": "positive",
                "ground_socket": "negative",
                "notes": "Standard stick electrode configuration"
            }
        },
        "specifications": {
            "input_voltage": ["120V", "240V"],
            "input_frequency": "50/60 Hz",
            "processes": ["MIG", "Flux-Cored", "TIG", "Stick"],
            "max_output": {
                "MIG_240V": "220A",
                "Flux-Cored_240V": "175A",
                "TIG_240V": "80A",
                "Stick_240V": "120A"
            },
            "wire_sizes": {
                "MIG": ["0.024\"", "0.030\"", "0.035\""],
                "Flux-Cored": ["0.035\"", "0.045\""]
            },
            "dimensions": "Width 30\", Height 36\", Depth 16\"",
            "weight": "170 lbs",
            "cooling": "Fan cooled"
        },
        "troubleshooting": [
            {
                "problem": "Porosity",
                "causes": ["Shielding gas issues (low flow, leaks, wind)", "Dirty material surface (oil, rust, paint)", "Arc length too long", "Contaminated wire or electrode", "Moisture on base metal"],
                "fixes": ["Check gas flow rate (25-35 CFH for MIG)", "Clean work area thoroughly with acetone or wire brush", "Reduce arc length", "Replace contaminated consumables", "Preheat damp material"]
            },
            {
                "problem": "Spatter",
                "causes": ["Voltage too high", "Wire speed too fast or slow", "Long arc length", "Wrong polarity", "Contaminated base metal"],
                "fixes": ["Reduce voltage setting", "Adjust wire speed to match voltage", "Shorten arc length", "Verify correct polarity (DCEP for MIG)", "Clean base metal before welding"]
            },
            {
                "problem": "Wire feed issues",
                "causes": ["Liner contamination or kink", "Wire tension too tight or loose", "Nozzle or contact tip clogged", "Wrong liner size for wire diameter", "Drive roll tension incorrect"],
                "fixes": ["Replace or clean liner", "Adjust drive roll tension - wire should slip under heavy load", "Replace contact tip and clean nozzle", "Match liner to wire size", "Adjust tension: too tight causes shaving, too loose causes slipping"]
            },
            {
                "problem": "Undercut",
                "causes": ["Travel speed too fast", "Voltage too high", "Improper torch angle", "Arc length too long"],
                "fixes": ["Slow down travel speed", "Reduce voltage", "Angle torch 10-15 degrees in direction of travel", "Maintain shorter arc length"]
            },
            {
                "problem": "Burn-through",
                "causes": ["Amperage/heat too high", "Travel speed too slow", "Material too thin for settings", "Gap between parts too large"],
                "fixes": ["Reduce amperage/wire speed", "Increase travel speed", "Use lower voltage setting or switch to 120V input", "Reduce gap or use backing material"]
            },
            {
                "problem": "No arc or arc won't start",
                "causes": ["Poor ground clamp connection", "Wrong polarity setting", "Electrode or wire not making contact", "Blown fuse or tripped breaker", "Duty cycle thermal protection active"],
                "fixes": ["Clean and clamp ground firmly to bare metal", "Check polarity matches process (DCEP for MIG, DCEN for TIG)", "Trim wire or replace electrode", "Check input power and reset breaker", "Wait for machine to cool down"]
            },
            {
                "problem": "Unstable arc or arc wander",
                "causes": ["Dirty or oxidized base metal", "Incorrect shielding gas or flow rate", "Worn contact tip", "Wind or drafts disturbing gas coverage", "Loose connections"],
                "fixes": ["Clean base metal to bright metal", "Verify correct gas and flow rate", "Replace contact tip", "Use wind screens or move to sheltered area", "Tighten all cable connections"]
            },
            {
                "problem": "Excessive penetration",
                "causes": ["Amperage too high", "Travel speed too slow", "Root gap too wide"],
                "fixes": ["Reduce amperage", "Increase travel speed", "Adjust fit-up to reduce gap"]
            },
            {
                "problem": "Lack of fusion or cold lap",
                "causes": ["Amperage/voltage too low", "Travel speed too fast", "Improper joint preparation", "Wrong torch angle"],
                "fixes": ["Increase voltage and wire speed", "Slow travel speed", "Ensure proper bevel and fit-up", "Direct arc into joint root"]
            },
            {
                "problem": "Cracking",
                "causes": ["Cooling too rapidly", "High carbon or alloy content in base metal", "Hydrogen embrittlement from moisture", "Excessive restraint on joint"],
                "fixes": ["Preheat base metal (especially thick sections)", "Use low-hydrogen electrodes", "Ensure dry consumables and clean surface", "Allow for thermal expansion during cooling"]
            }
        ],
        "extracted_at": "default"
    }
