import cv2
import numpy as np
from app.model import model

# Categories
RECYCLABLE = ['cardboard_box','can','plastic_bottle_cap','plastic_bottle','reuseable_paper']
NON_RECYCLABLE = ['plastic_bag','scrap_paper','stick','plastic_cup','snack_bag','plastic_box','straw','plastic_cup_lid','scrap_plastic','cardboard_bowl','plastic_cultery']
HAZARDOUS = ['battery','chemical_spray_can','chemical_plastic_bottle','chemical_plastic_gallon','light_bulb','paint_bucket']

def classify(label):
    if label in RECYCLABLE:
        return 'Recyclable'
    elif label in NON_RECYCLABLE:
        return 'Non-Recyclable'
    elif label in HAZARDOUS:
        return 'Hazardous'
    return 'Unknown'

def detect_and_classify(image_bytes):
    np_arr = np.frombuffer(image_bytes, np.uint8)
    img_bgr = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)

    results = model.predict(img_rgb, verbose=False)[0]

    detections = []
    for box in results.boxes:
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        conf = box.conf[0].item()
        cls_id = int(box.cls[0].item())
        label = model.names[cls_id]
        category = classify(label)

        detections.append({
            "label": label,
            "category": category,
            "confidence": conf,
            "box": [x1, y1, x2, y2]
        })

    return detections
