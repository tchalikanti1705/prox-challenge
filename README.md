# Vulcan OmniPro 220 — Multimodal Expert Agent

An AI-powered technical advisor for the Vulcan OmniPro 220 multiprocess welding system. Ask it anything about setup, polarity, duty cycles, troubleshooting — and it answers with **generated diagrams, interactive calculators, and manual images**, not just text.

<img src="product.webp" alt="Vulcan OmniPro 220" width="380" /> <img src="product-inside.webp" alt="Vulcan OmniPro 220 — inside panel" width="380" />

---

## Quick Start

```bash
git clone https://github.com/tchalikanti1705/prox-challenge
cd prox-challenge
cp .env.example .env          # Add your ANTHROPIC_API_KEY
pip install -r requirements.txt
cd backend && python app.py   # Server starts on http://localhost:8000
```

Open **http://localhost:8000** in your browser. That's it.

> **Requirements:** Python 3.10+, Anthropic API key  
> **No build step.** No npm. No Docker. No database. Clone → install → run.

---

## What It Does

This isn't a chatbot that describes things in paragraphs. When you ask about polarity, **it draws you the wiring diagram**. When you ask about duty cycles, **it renders an interactive table with your query highlighted**. When you ask about troubleshooting, **it generates a visual flowchart**.

### Example: "What polarity do I need for TIG welding?"

The agent:
1. Calls the `lookup_polarity` tool → gets exact data: DCEN, torch → negative, ground → positive
2. Generates an SVG wiring diagram showing which cable goes in which socket
3. Explains it in plain English underneath

The user sees text + a rendered diagram inline in the chat — not code, not a description of a diagram.

### Example: "What's the duty cycle for MIG at 200A on 240V?"

The agent:
1. Calls the `lookup_duty_cycle` tool → gets the exact percentage from the manual
2. Generates an HTML table showing all MIG duty cycles at 240V with the 200A row highlighted
3. Explains what duty cycle means in practical terms ("you can weld for X minutes, then rest Y minutes")

### Example: "I'm getting porosity in my flux-cored welds"

The agent:
1. Calls `get_troubleshooting` → gets causes and fixes from the manual's troubleshooting matrix
2. Generates an SVG flowchart walking through each diagnostic step
3. Offers to go deeper on any specific cause

---

## Architecture

```
┌──────────────────────────────────────────────────┐
│           Frontend (single HTML file)             │
│  Chat UI │ Artifact Renderer │ Voice I/O │ Upload │
└────────────────────┬─────────────────────────────┘
                     │ SSE stream
┌────────────────────┼─────────────────────────────┐
│           Backend (FastAPI + Python)               │
│                    │                               │
│    ┌───────────────▼────────────────────┐         │
│    │     Claude Sonnet 4 (Anthropic API) │         │
│    │     System prompt + 6 tool defs     │         │
│    └───┬───────┬───────┬───────┬────────┘         │
│        │       │       │       │                   │
│    ┌───▼──┐┌───▼──┐┌───▼──┐┌───▼──┐              │
│    │Search││Duty  ││Polar-││Troub-│ + 2 more      │
│    │      ││Cycle ││ity   ││shoot │               │
│    └───┬──┘└───┬──┘└───┬──┘└───┬──┘              │
│        └───────┴───────┴───────┘                   │
│                    │                               │
│    ┌───────────────▼────────────────────┐         │
│    │   Knowledge Store (in-memory JSON)  │         │
│    │   50 chunks │ structured data │ 51 imgs      │
│    └─────────────────────────────────────┘         │
└────────────────────────────────────────────────────┘
```

### Layered design

| Layer | Files | What it does |
|-------|-------|-------------|
| **Frontend** | `frontend/index.html` | Chat UI, parses `<artifact>` tags into rendered SVG/HTML, voice input/output via Web Speech API, image upload |
| **API** | `backend/api/routes.py` | 3 endpoints: `POST /api/chat` (SSE stream), `GET /api/images/:id`, `GET /api/health` |
| **Agent** | `backend/agent/client.py` | Agentic loop: sends to Claude → if tool call → execute → send result back → repeat (max 10 turns) |
| **Tools** | `backend/agent/tools/*.py` | 6 specialized tools, each reads from knowledge store |
| **Knowledge** | `backend/knowledge/store.py` | Singleton loaded at startup, serves all data from pre-extracted JSON |
| **Extraction** | `backend/scripts/extract.py` | One-time pipeline: PDF → text chunks + embeddings + images + structured data via Claude Vision |

### Request flow

```
User asks question
  → Frontend sends POST /api/chat with conversation history
    → Backend opens SSE stream
      → Agent sends to Claude with system prompt + tool definitions
        → Claude decides: "I need duty cycle data" → calls lookup_duty_cycle tool
          → Tool reads from knowledge store → returns JSON
            → Agent sends result back to Claude
              → Claude writes answer + generates <artifact type="svg"> diagram
                → Backend streams text tokens to frontend in real time
                  → Frontend parses response: text → chat bubble, artifact → rendered SVG
                    → If TTS enabled, browser speaks the text aloud
```

---

## Design Decisions

### Why direct Anthropic API instead of Agent SDK?

The Claude Agent SDK (`claude-agent-sdk`) wraps Claude Code's CLI — designed for code-editing agents that read/write files. Our use case is a **chat agent with tool use**, where the Messages API with streaming is more natural and gives us fine-grained control over the SSE stream.

I implemented the tools in both patterns:
- `backend/agent/client.py` — Direct API with `messages.stream()` (used in production)
- `backend/agent/sdk_tools.py` — Claude Agent SDK MCP tools with `@tool` decorators (available as alternative)

The direct API gives us streaming token delivery, which is critical for UX — the user sees words appear in real time instead of waiting for the full response.

### Why a single HTML file for the frontend?

The challenge says "we should be running your agent within 2 minutes." A React/Next.js app adds `npm install` (30+ seconds), a build step, and node_modules. A single HTML file with inline CSS/JS:
- Opens instantly from FastAPI's static file serving
- Zero build configuration
- Still supports artifact rendering, voice I/O, image upload, chat history (localStorage), and streaming

### Why pre-extracted knowledge (not runtime RAG)?

The manual doesn't change. Running extraction at startup would mean:
- Slower startup (30+ seconds for PDF processing)
- Claude Vision API calls on every restart (costs money)
- Risk of extraction failure blocking the server

Instead, extraction runs once (`python backend/scripts/extract.py`), saves to JSON, and the JSON ships with the repo. Server startup loads JSON into memory in milliseconds.

### Why keyword embeddings instead of OpenAI embeddings?

To avoid requiring a second API key. The challenge says "single API key via .env" (Anthropic). Keyword-based search with 44 welding-specific dimensions works well enough for a 50-chunk manual. The system prompt + Claude's own reasoning compensates for any retrieval gaps.

To upgrade: set `USE_OPENAI_EMBEDDINGS=True` in `config.py` and add `OPENAI_API_KEY` to `.env`.

### How the artifact system works

The system prompt instructs Claude to wrap visual content in `<artifact>` tags:

```
<artifact type="svg" title="TIG polarity diagram">
<svg viewBox="0 0 600 400">...</svg>
</artifact>
```

The frontend's `renderContent()` function:
1. Regex-matches `<artifact type="..." title="...">...</artifact>` blocks
2. Splits response into text parts and artifact parts
3. Text → rendered as Markdown via `marked()`
4. `type="svg"` → parsed via DOMParser, sanitized (scripts removed), rendered inline
5. `type="html"` → rendered in a sandboxed iframe (allow-scripts only)
6. `type="image"` → loaded from `/api/images/{id}`

During streaming, incomplete artifacts show a loading placeholder instead of raw code.

---

## Knowledge Extraction Pipeline

Three PDFs processed → three JSON outputs:

| Input | Extractor | Output |
|-------|-----------|--------|
| 48-page owner's manual | PyMuPDF text extraction + section detection | `chunks.json` (50 chunks with embeddings) |
| All 3 PDFs | PyMuPDF image extraction + auto-tagging | `image_catalog.json` (51 images with metadata) |
| Table-heavy pages | Claude Vision API reads images of tables | `structured_data.json` (duty cycles, polarity, specs, troubleshooting) |

### structured_data.json contains:

**Duty cycles** — exact matrix from the manual:
```json
{
  "MIG": {
    "240V": {"100A": 40, "115A": 100, "200A": 25},
    "120V": {"75A": 100, "100A": 40}
  }
}
```

**Polarity** — which socket for each process:
```json
{
  "TIG": {
    "type": "DCEN (Straight Polarity)",
    "torch_socket": "negative",
    "ground_socket": "positive"
  }
}
```

**Troubleshooting** — 19 problems with causes and fixes, from both the manual's troubleshooting matrix and weld diagnosis section.

**Specifications** — input voltage, processes, max output, wire sizes, dimensions, weight.

---

## Tools Reference

| Tool | When Claude uses it | What it returns |
|------|-------------------|-----------------|
| `search_knowledge` | General questions, setup guides, safety | Top-5 most relevant manual sections |
| `lookup_duty_cycle` | Any duty cycle / amperage / weld time question | Exact percentage + all ratings at that voltage |
| `lookup_polarity` | Wiring, connections, terminal, socket questions | Polarity type + torch socket + ground socket |
| `get_troubleshooting` | User reports a problem or defect | Causes + step-by-step fixes |
| `search_manual_images` | Answer needs a visual from the manual | Image metadata (ID, page, tags, context) |
| `get_specifications` | Machine capability questions | All specs as JSON |

The system prompt explicitly tells Claude: **"NEVER guess about duty cycles or polarity. ALWAYS use the tool first."** This prevents hallucination on safety-critical data.

---

## Features

### Multimodal output
- **SVG diagrams** — wiring schematics, polarity setups, flowcharts generated in real time
- **HTML widgets** — duty cycle tables with highlighting, spec cards, comparison charts
- **Interactive calculators** — duty cycle calculator, settings configurator
- **Manual images** — 51 extracted images served via API, surfaced when relevant

### Voice I/O
- **Speech-to-text** — click the microphone button, speak your question (Web Speech API)
- **Text-to-speech** — toggle TTS on, the agent reads its response aloud
- Zero external dependencies, runs entirely in the browser

### Image upload
- Upload a photo of your weld, machine, or setup
- Claude Vision analyzes the image and compares with known defect patterns
- Agent surfaces relevant manual images for comparison

### Streaming responses
- Text appears word-by-word as Claude generates it
- Incomplete artifacts show a loading spinner until complete
- Tool calls show friendly status messages ("Searching the manual...", "Looking up duty cycle data...")

### Chat history
- Conversations persist in localStorage
- Sidebar shows previous chats with timestamps
- New chat / delete chat / clear all

---

## Project Structure

```
prox-challenge/
├── frontend/
│   └── index.html                  # Single-file SPA
│
├── backend/
│   ├── app.py                      # Entry point — starts FastAPI + serves frontend
│   ├── config.py                   # All env vars and paths
│   │
│   ├── agent/
│   │   ├── client.py               # Agentic loop with streaming
│   │   ├── prompts.py              # System prompt
│   │   └── tools/
│   │       ├── __init__.py          # Tool registry
│   │       ├── search_tool.py
│   │       ├── duty_cycle_tool.py
│   │       ├── polarity_tool.py
│   │       ├── troubleshoot_tool.py
│   │       ├── image_tool.py
│   │       └── specs_tool.py
│   │
│   ├── knowledge/
│   │   ├── store.py                # Singleton data store
│   │   ├── extractor.py            # PDF text + image extraction
│   │   ├── vision_extractor.py     # Claude Vision for tables
│   │   ├── embeddings.py           # Keyword vectors for search
│   │   └── data/                   # Pre-extracted (ships with repo)
│   │       ├── chunks.json
│   │       ├── structured_data.json
│   │       ├── image_catalog.json
│   │       └── images/             # 51 extracted PNGs
│   │
│   ├── api/
│   │   ├── routes.py               # FastAPI endpoints
│   │   └── models.py               # Pydantic models
│   │
│   └── scripts/
│       └── extract.py              # One-time extraction CLI
│
├── files/                          # Source PDFs
│   ├── owner-manual.pdf
│   ├── quick-start-guide.pdf
│   └── selection-chart.pdf
│
├── .env.example
├── requirements.txt
├── run.py                          # Convenience launcher
├── Dockerfile
└── docker-compose.yml
```

---

## Re-extracting the Knowledge Base

The knowledge base ships pre-extracted. To rebuild it (e.g., if you modify the extraction pipeline):

```bash
cd backend
python scripts/extract.py
```

This will:
1. Read all PDFs from `files/`
2. Extract text chunks + generate embeddings
3. Extract images + auto-tag them
4. Use Claude Vision to read duty cycle tables and specs from page images
5. Save everything to `knowledge/data/`

**Cost:** ~$0.50 in Claude API calls for the Vision extraction.

---

## API Reference

### POST /api/chat
Send a message and stream the response.

**Request:**
```json
{
  "messages": [
    {"role": "user", "content": "What polarity for TIG?"},
    {"role": "assistant", "content": "For TIG welding..."},
    {"role": "user", "content": "Show me a diagram"}
  ]
}
```

**Response:** Server-Sent Events stream
```
data: {"type": "thinking", "content": "Checking polarity settings..."}
data: {"type": "text", "content": "For TIG welding, you'll use "}
data: {"type": "text", "content": "DCEN polarity..."}
data: {"type": "text", "content": "<artifact type=\"svg\"..."}
data: {"type": "done"}
```

### GET /api/images/{image_id}
Serve an extracted manual image.

### GET /api/health
```json
{
  "status": "ok",
  "knowledge_loaded": true,
  "chunks_count": 50,
  "images_count": 51
}
```

---

## Testing

Ask these questions to verify the agent works correctly:

| Question | Expected behavior |
|----------|------------------|
| "What's the duty cycle for MIG at 200A on 240V?" | Exact number + visual duty cycle table |
| "What polarity for TIG welding?" | DCEN + SVG wiring diagram |
| "I'm getting porosity in my flux-cored welds" | Troubleshooting flowchart |
| "Show me the front panel controls" | Manual image surfaced |
| "Can I weld aluminum with this machine?" | Nuanced answer about DC-only TIG limitation |
| "I want to weld 1/4 inch mild steel" | Settings configurator with process recommendation |

---

## Tech Stack

| Component | Technology | Why |
|-----------|-----------|-----|
| LLM | Claude Sonnet 4 | Best reasoning + tool use + vision |
| Backend | FastAPI (Python) | Async streaming, zero boilerplate |
| Frontend | Vanilla HTML/CSS/JS | Zero build step, instant setup |
| PDF processing | PyMuPDF (fitz) | Fast, reliable text + image extraction |
| Table extraction | Claude Vision API | Reads complex tables that exist only as images |
| Search | Keyword embeddings (44-dim) | No second API key needed |
| Voice | Web Speech API (browser) | Zero cost, zero dependencies |
| Streaming | Server-Sent Events | Real-time token delivery |

---

## What I'd Build Next

Given more time, these are the improvements I'd prioritize:

1. **OpenAI embeddings** — swap keyword vectors for `text-embedding-3-small` for dramatically better search recall
2. **Conversation memory** — let the agent reference earlier messages ("you mentioned you're using 240V earlier")
3. **Hosted demo** — deploy to Railway/Render so reviewers can try without cloning
4. **Video walkthrough** — record a demo covering all 5 killer test questions
5. **Settings configurator** — dedicated interactive widget for material + thickness → recommended settings
6. **WebSocket** — replace SSE with WebSocket for bidirectional communication
7. **PDF page rendering** — show the actual manual page as a rendered image when referencing it

---

Built by [Teja Chalikanti](https://teja-chalikanti.vercel.app) | [GitHub](https://github.com/tchalikanti1705)
