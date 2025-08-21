import os
import json
import cv2
import matplotlib.pyplot as plt
from ultralytics import YOLO
import shutil


# ----------------------
# Config
# ----------------------
model = YOLO(r"D:\SWARAJ_POC\Yolo_code\best.pt")  # Load a pretrained model
image_path = r"D:\SWARAJ_POC\Yolo_code\test2.png"

# Output directories
output_dir = "output"
annotated_dir = os.path.join(output_dir, "annotated")
json_dir = os.path.join(output_dir, "annotations")
os.makedirs(output_dir, exist_ok=True)
os.makedirs(annotated_dir, exist_ok=True)
os.makedirs(json_dir, exist_ok=True)

# ----------------------
# Save input image copy
# ----------------------
image_name = os.path.basename(image_path)
shutil.copy(image_path, os.path.join(output_dir, image_name))

# ----------------------
# Run YOLO
# ----------------------
results = model(image_path, conf=0.75)

# Load image for drawing
img = cv2.imread(image_path)
img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

# Prepare JSON annotations
annotations = []

# Loop through detections
for result in results:
    xyxy = result.boxes.xyxy.cpu().numpy()  # Bounding boxes
    confs = result.boxes.conf.cpu().numpy()  # Confidence scores
    names = [result.names[int(cls)] for cls in result.boxes.cls.cpu().numpy()]  # Class names

    for (x1, y1, x2, y2), conf, name in zip(xyxy, confs, names):
        # Save annotation
        annotations.append({
            "class": name,
            "confidence": float(conf),
            "bbox": [float(x1), float(y1), float(x2), float(y2)]  # [x_min, y_min, x_max, y_max]
        })

        # Draw rectangle & label
        cv2.rectangle(img, (int(x1), int(y1)), (int(x2), int(y2)), (255, 0, 0), 2)
        cv2.putText(img, f"{name} {conf:.2f}", (int(x1), int(y1) - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 139), 2)

# ----------------------
# Save annotated image
# ----------------------
annotated_path = os.path.join(annotated_dir, f"annotated_{image_name}")
cv2.imwrite(annotated_path, cv2.cvtColor(img, cv2.COLOR_RGB2BGR))

# ----------------------
# Save annotations as JSON
# ----------------------
json_path = os.path.join(json_dir, f"{os.path.splitext(image_name)[0]}.json")
with open(json_path, "w") as f:
    json.dump(annotations, f, indent=4)

print(f"✅ Image saved at: {annotated_path}")
print(f"✅ Annotations saved at: {json_path}")
