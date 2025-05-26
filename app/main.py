from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from ultralytics import YOLO
from pathlib import Path
from datetime import datetime
import os
import cv2
import uuid
import numpy as np
import psycopg2
import shutil

# --- CONFIGURATION
UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "output"
TEMP_FOLDER = "temp"
os.makedirs(TEMP_FOLDER, exist_ok=True)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
WEIGHTS_PATH = "weights/best.pt"

RECYCLABLE = ['cardboard_box', 'can', 'plastic_bottle_cap', 'plastic_bottle', 'reuseable_paper']
NON_RECYCLABLE = ['plastic_bag', 'scrap_paper', 'stick', 'plastic_cup', 'snack_bag',
                  'plastic_box', 'straw', 'plastic_cup_lid', 'scrap_plastic', 'cardboard_bowl', 'plastic_cultery']
HAZARDOUS = ['battery', 'chemical_spray_can', 'chemical_plastic_bottle', 'chemical_plastic_gallon',
             'light_bulb', 'paint_bucket']

# --- Initialize app
app = FastAPI()
model = YOLO(WEIGHTS_PATH)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- DB Connection (adjust credentials)
def get_connection():
    return psycopg2.connect(
        dbname="railway",
        user="postgres",
        password="jmoKDpufnLxSCMgGkKqIgLiPyJQdyYBU",
        host="tramway.proxy.rlwy.net",
        port="44797"
    )

# --- Classification helper
def classify(label):
    if label in RECYCLABLE:
        return 'Recyclable'
    elif label in NON_RECYCLABLE:
        return 'Non-Recyclable'
    elif label in HAZARDOUS:
        return 'Hazardous'
    return 'Unknown'

# --- Detection core
def detect_and_classify_bytes(image_bytes):
    nparr = np.frombuffer(image_bytes, np.uint8)
    img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)

    results = model.predict(img_rgb, verbose=False)[0]
    detections = []

    for box in results.boxes:
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        conf = float(box.conf[0])
        cls_id = int(box.cls[0])
        label = model.names[cls_id]
        category = classify(label)

        detections.append({
            "label": label,
            "category": category,
            "confidence": round(conf, 2),
            "bbox": [x1, y1, x2, y2]
        })

        cv2.rectangle(img_bgr, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(img_bgr, f"{label} ({category})", (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

    return img_bgr, detections

# --- /process/ endpoint
@app.post("/analyze-image/")
async def analyze_image(
    file: UploadFile = File(...),
):
    try:
        image_bytes = await file.read()
        filename = f"{uuid.uuid4().hex}_{file.filename}"
        raw_path = os.path.join(UPLOAD_FOLDER, filename)

        with open(raw_path, "wb") as f:
            f.write(image_bytes)

        img_bgr, detections = detect_and_classify_bytes(image_bytes)

        # Save annotated image to TEMP folder
        temp_path = os.path.join(TEMP_FOLDER, filename)
        cv2.imwrite(temp_path, img_bgr)

        return {
            "message": "Detection successful. Awaiting confirmation.",
            "temp_filename": filename,
            "detections": detections,
            "preview_image_url": f"/temp_image/{filename}"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@app.post("/confirm/")
async def confirm_pickup(
    temp_filename: str = Form(...),
    user_id: int = Form(...),
    lat: float = Form(...),
    lng: float = Form(...),
    address: str = Form(None)
):
    try:
        temp_path = os.path.join(TEMP_FOLDER, temp_filename)
        final_path = os.path.join(OUTPUT_FOLDER, temp_filename)

        if not os.path.exists(temp_path):
            raise HTTPException(status_code=404, detail="Temporary image not found")

        # Move file to permanent folder
        shutil.move(temp_path, final_path)

        # Re-run detection to count points (optional; or return point count from /process/)
        with open(os.path.join(UPLOAD_FOLDER, temp_filename), "rb") as f:
            image_bytes = f.read()
        _, detections = detect_and_classify_bytes(image_bytes)

        # Save to DB
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO pickup_spots 
            (user_id, latitude, longitude, created_at, photo_url, address, is_disposed, points) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id;
        """, (
            user_id,
            lat,
            lng,
            datetime.now(),
            temp_filename,
            address,
            False,
            len(detections)
        ))
        pickup_id = cur.fetchone()[0]

        conn.commit()
        cur.close()
        conn.close()

        return {
            "message": "Pickup confirmed and saved",
            "pickup_id": pickup_id,
            "points": len(detections)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/temp_image/{filename}")
def get_temp_image(filename: str):
    file_path = os.path.join(TEMP_FOLDER, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(file_path)


# --- /upload/ endpoint (raw upload without detection)
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
            INSERT INTO pickup_spots 
            (user_id, latitude, longitude, created_at, address, photo_url, is_disposed, points)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id;
        """, (
            user_id,
            lat,
            lng,
            pickup_time,
            address,
            filename,
            False,
            0
        ))


        pickup_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()

        return {"message": "Upload successful", "pickup_id": pickup_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- /user_points/ endpoint
@app.get("/user_points/{user_id}")
def get_user_points(user_id: int):
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT SUM(points), json_agg(json_build_object(
                'id', id,
                'latitude', latitude,
                'longitude', longitude,
                'is_disposed', is_disposed,
                'photo_url', photo_url,
                'points', points,
                'address', address,
                'created_at', created_at
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

# --- Serve annotated images
@app.get("/image/{filename}")
def get_image(filename: str):
    file_path = os.path.join(OUTPUT_FOLDER, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(file_path)
