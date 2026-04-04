# Quick Start Guide

## 1. Setup (5 minutes)

### Get API Key
1. Go to https://console.anthropic.com
2. Create API key
3. Save to `.env`:
   ```
   ANTHROPIC_API_KEY=sk-...
   ```

### Install Python Dependencies
```bash
cd backend
pip install -r requirements.txt
```

## 2. Extract Knowledge (2-3 minutes)

```bash
python backend/scripts/extract.py
```

Processes PDFs and creates knowledge database. You'll see:
```
📄 STEP 1: Extracting text and images...
✓ Extracted 150 text chunks
✓ Extracted 25 images

🔢 STEP 2: Generating embeddings...
✓ Generated embeddings for 150 chunks

👁️ STEP 3: Extracting with Claude Vision...
✓ Extracted structured data

💾 STEP 4: Saving...
✓ Done!
```

## 3. Start Backend (30 seconds)

```bash
python backend/app.py
```

You'll see:
```
🚀 Starting OmniPro 220 Expert Agent...
✓ Backend ready!
   - 150 text chunks loaded
   - 25 images cataloged
   - Processes: ['MIG', 'Flux-Cored', 'TIG', 'Stick']
📍 API running at http://0.0.0.0:8000
```

## 4. Open Frontend

Open `frontend/index.html` in your browser

Or serve HTTP:
```bash
python -m http.server 3000
# Open http://localhost:3000/frontend/
```

## 5. Start Chatting!

Examples to try:
- "What's the duty cycle for MIG at 200A on 240V?"
- "How do I set up TIG welding? Show me a diagram."
- "I'm getting porosity in my welds. What should I check?"
- "What are the specifications for this machine?"
- Try uploading a weld photo for diagnosis

---

## Troubleshooting

**"ANTHROPIC_API_KEY not set"**
→ Create `.env` file with your API key

**"No PDF files found"**
→ PDFs must be in `files/` directory

**"Backend not responding" in frontend**
→ Make sure `python backend/app.py` is running

**"Connection refused" when starting backend**
→ Check if port 8000 is in use: `lsof -i :8000` (Mac/Linux)

---

## Architecture at a Glance

```
User Question
    ↓
Frontend (HTML chat)
    ↓ HTTP POST
Backend API (FastAPI)
    ↓
Claude Agent (with tools)
    ↓ calls tools
Tools (lookup special data)
    ↓ read from
Knowledge Store (JSON files in memory)
    ↓
Response streams back with text + visuals
```

---

## What's Happening Behind the Scenes

1. **Extraction** - PDFs → text chunks, images, duty cycle tables
2. **Embedding** - Text chunks → vectors for smart searching
3. **Storage** - Everything in JSON files for fast loading
4. **Agent Loop** - Claude reads question → calls tools → gets data → generates response
5. **Streaming** - Response streamed to frontend in real-time

---

## Key Files

- `backend/app.py` - Start the server
- `backend/scripts/extract.py` - Build knowledge from PDFs
- `backend/config.py` - Settings and paths
- `backend/agent/prompts.py` - System prompt (controls how Claude behaves)
- `backend/agent/tools/*.py` - 6 specialized tools
- `frontend/index.html` - Web interface

---

## Next Steps

- ✅ Try asking duty cycle questions
- ✅ Try polarity/wiring setup questions
- ✅ Try troubleshooting ("I have porosity")
- ✅ Try uploading a weld image
- ✅ Look at generated diagrams and tables

For more details, see `README_IMPLEMENTATION.md` in the root.

Enjoy! 🔥⚡
