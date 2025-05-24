import os
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from app.detect import detect_and_classify
import uvicorn

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "Waste Detection API is running!"}

@app.post("/detect/")
async def detect(file: UploadFile = File(...)):
    image_bytes = await file.read()
    result = detect_and_classify(image_bytes)
    return {"detections": result}

# Example placeholder for upload to Cloudflare R2 (implement later)
# from some_module import upload_image_to_r2

@app.post("/upload/")
async def upload_image(file: UploadFile = File(...)):
    image_bytes = await file.read()
    filename = file.filename
    # url = upload_image_to_r2(image_bytes, filename)
    # For now just return filename for demo
    return {"filename": filename}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
