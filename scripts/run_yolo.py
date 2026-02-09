from pathlib import Path
from ultralytics import YOLO

ROOT = Path(__file__).parent.parent
OUTPUT = ROOT / "images" / "output"

# Load YOLO26 Nano model (auto-downloads weights on first run)
model = YOLO("yolo26n.pt")

# Run inference on the cleaned image
results = model(str(OUTPUT / "mysterious_no_bg.png"))

# Process detection results
for result in results:
    boxes = result.boxes
    if len(boxes) == 0:
        print("No objects detected!")
    else:
        for i in range(len(boxes)):
            x1, y1, x2, y2 = boxes.xyxy[i].tolist()
            confidence = boxes.conf[i].item()
            class_id = int(boxes.cls[i].item())
            class_name = result.names[class_id]
            print(f"{class_name}: {confidence:.4f}  bbox=({x1:.0f}, {y1:.0f}, {x2:.0f}, {y2:.0f})")

    # Save annotated image
    result.save(filename=str(OUTPUT / "yolo_result.png"))
    print("\nAnnotated image saved to yolo_result.png")
