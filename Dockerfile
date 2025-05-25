# Use a slim base image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies (only essentials)
RUN apt-get update && apt-get install -y \
    gcc \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install with no cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy only the necessary source code
COPY app/ app/

# Expose the port
EXPOSE 10000

# Run the app
CMD ["uvicorn", "app.main:app", "--host=0.0.0.0", "--port=10000"]
