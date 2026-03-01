# --- Stage 1: Build the Frontend ---
FROM node:18-slim AS build-stage

WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

# --- Stage 2: Build the Backend ---
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV MODE cloud
ENV PORT 7860
ENV DATA_DIR /app/data
ENV INDEX_DIR /app/data/index

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Copy the built frontend from Stage 1
COPY --from=build-stage /app/dist ./dist

# Pre-download the embedding model
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# Create data directory with permissions for Hugging Face (which runs as a non-root user)
RUN mkdir -p /app/data/index && chmod -R 777 /app/data

# Expose the API port (HF uses 7860 by default)
EXPOSE 7860

# Run in cloud mode
CMD ["python", "main.py", "api"]
