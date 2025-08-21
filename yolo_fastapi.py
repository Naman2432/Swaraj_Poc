import os
import json
import cv2
import shutil
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
from ultralytics import YOLO

# ----------------------
# Config
# ----------------------
MODEL_PATH = "best.pt"
OUTPUT_DIR = "output"
ANNOTATED_DIR = os.path.join(OUTPUT_DIR, "annotated")
JSON_DIR = os.path.join(OUTPUT_DIR, "annotations")
UPLOAD_DIR = os.path.join(OUTPUT_DIR, "uploads")

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(ANNOTATED_DIR, exist_ok=True)
os.makedirs(JSON_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ----------------------
# Load YOLO model once at startup
# ----------------------
model = YOLO(MODEL_PATH)

# ----------------------
# FastAPI app
# ----------------------
app = FastAPI(title="YOLO FastAPI Inference")


@app.post("/predict")
async def predict(file: UploadFile = File(...)):
    # ----------------------
    # Save uploaded image
    # ----------------------
    image_name = file.filename
    upload_path = os.path.join(UPLOAD_DIR, image_name)

    with open(upload_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # ----------------------
    # Run YOLO inference
    # ----------------------
    results = model(upload_path, conf=0.75)

    img = cv2.imread(upload_path)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    annotations = []

    for result in results:
        xyxy = result.boxes.xyxy.cpu().numpy()  # Bounding boxes
        confs = result.boxes.conf.cpu().numpy()  # Confidence scores
        names = [result.names[int(cls)] for cls in result.boxes.cls.cpu().numpy()]  # Class names

        for (x1, y1, x2, y2), conf, name in zip(xyxy, confs, names):
            # Save annotation
            annotations.append({
                "class": name,
                "confidence": float(conf),
                "bbox": [float(x1), float(y1), float(x2), float(y2)]
            })

            # Draw rectangle & label
            cv2.rectangle(img, (int(x1), int(y1)), (int(x2), int(y2)), (255, 0, 0), 2)
            cv2.putText(img, f"{name} {conf:.2f}", (int(x1), int(y1) - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 139), 2)

    # ----------------------
    # Save annotated image
    # ----------------------
    annotated_path = os.path.join(ANNOTATED_DIR, f"annotated_{image_name}")
    cv2.imwrite(annotated_path, cv2.cvtColor(img, cv2.COLOR_RGB2BGR))

    # ----------------------
    # Save annotations JSON
    # ----------------------
    json_path = os.path.join(JSON_DIR, f"{os.path.splitext(image_name)[0]}.json")
    with open(json_path, "w") as f:
        json.dump(annotations, f, indent=4)

    # ----------------------
    # Return response
    # ----------------------
    return JSONResponse({
        "uploaded_image": upload_path,
        "annotated_image": annotated_path,
        "annotations_json": json_path,
        "annotations": annotations
    })
