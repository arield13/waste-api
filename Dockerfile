FROM python:3.10-slim-bullseye

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copy all your source code (adjust if your source layout is different)
COPY . .

# Use Railway's PORT env variable (default fallback 8080)
ENV PORT=8080

EXPOSE $PORT

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port $PORT"]
