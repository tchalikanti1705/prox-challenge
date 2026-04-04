FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libmupdf-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY backend ./backend
COPY files ./files

# Ensure knowledge directory exists
RUN mkdir -p backend/knowledge/data/images

# Extract knowledge base
RUN python backend/scripts/extract.py

# Start server
CMD ["python", "backend/app.py"]

EXPOSE 8000
