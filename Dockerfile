FROM python:3.10-alpine

WORKDIR /app

# Install build dependencies using apk (Alpine package manager)
RUN apk add --no-cache \
    gcc \
    musl-dev \
    libjpeg-turbo-dev \
    zlib-dev \
    libpng \
    libxrender \
    libsm \
    libxext

# Copy requirements and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app source code
COPY . .

# Use Railway's PORT env variable (fallback to 8080)
ENV PORT=8080
EXPOSE $PORT

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port $PORT"]
