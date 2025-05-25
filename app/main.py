import os
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.detect import detect_and_classify
from app.db import get_connection
from datetime import datetime
import shutil
import uuid
import uvicorn

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

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

@app.post("/upload/")
async def upload_image(
    file: UploadFile = File(...),
    user_id: int = Form(...),
    lat: float = Form(...),
    lng: float = Form(...),
    address: str = Form(None),
    time: str = Form(None)
):
    try:
        image_bytes = await file.read()
        filename = f"{uuid.uuid4().hex}_{file.filename}"
        file_path = os.path.join(UPLOAD_FOLDER, filename)

        with open(file_path, "wb") as f:
            f.write(image_bytes)

        pickup_time = datetime.fromisoformat(time) if time else datetime.now()

        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO pickup_spots (user_id, lat, lng, time, address, photo_path)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id;
        """, (user_id, lat, lng, pickup_time, address, filename))

        pickup_id = cur.fetchone()[0]
        conn.commit()

        cur.close()
        conn.close()

        return {"message": "Upload successful", "pickup_id": pickup_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/user_points/{user_id}")
def get_user_points(user_id: int):
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT SUM(points), json_agg(json_build_object(
                'id', id,
                'lat', lat,
                'lng', lng,
                'is_disposed', is_disposed,
                'photo_path', photo_path,
                'points', points
            ))
            FROM pickup_spots
            WHERE user_id = %s;
        """, (user_id,))

        result = cur.fetchone()
        total_points = result[0] or 0
        pickups = result[1] or []

        cur.close()
        conn.close()

        return {"user_id": user_id, "points": total_points, "pickups": pickups}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)