FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libmupdf-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code + frontend + source PDFs
COPY backend ./backend
COPY frontend ./frontend
COPY files ./files

# Knowledge base is pre-extracted and committed to repo
# No need to run extract.py at build time

EXPOSE 8000

# Start server from backend directory so uvicorn can find "app:app" module
WORKDIR /app/backend
CMD ["python", "app.py"]
