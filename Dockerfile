FROM python:3.11-slim

WORKDIR /app

# Install system audio/compiler libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libsndfile1 \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Expose FastAPI backend (8000) and Streamlit dashboard (8501)
EXPOSE 8000 8501

# Run the unified orchestrator
CMD ["python", "run_system.py"]
