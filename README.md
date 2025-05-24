# Waste Detection API

This is a FastAPI-based backend service for waste detection in images. It processes uploaded images and returns detected waste categories with bounding boxes.

---

## Features

- Upload images to detect waste types and locations.
- CORS enabled for easy frontend integration.
- Designed to store and retrieve images via Cloudflare R2 (to be integrated).
- Ready for deployment on [Railway](https://railway.app) with GitHub integration.

---

## Requirements

- Python 3.8+
- See `requirements.txt` for dependencies.

---

## Setup and Run Locally

1. Clone the repository:

   ```bash
   git clone https://github.com/yourusername/waste-detection-api.git
   cd waste-detection-api

2. Create and activate a virtual environment
    python -m venv venv
    source venv/bin/activate   # On Windows: venv\Scripts\activate

3. Install dependencies:
    pip install -r requirements.txt

4. Run the app:
    uvicorn app.main:app --reload

5. The API will be accessible at http://127.0.0.1:8000