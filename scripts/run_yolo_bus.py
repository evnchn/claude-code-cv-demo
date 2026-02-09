from ultralytics import YOLO

model = YOLO("yolo26n.pt")

results = model("/Users/evnchn/ClaudeCodeCV/bus.jpg")

for result in results:
    boxes = result.boxes
    if len(boxes) == 0:
        print("No objects detected!")
    else:
        print(f"Detected {len(boxes)} objects:\n")
        for i in range(len(boxes)):
            x1, y1, x2, y2 = boxes.xyxy[i].tolist()
            confidence = boxes.conf[i].item()
            class_id = int(boxes.cls[i].item())
            class_name = result.names[class_id]
            print(f"  {class_name}: {confidence:.4f}  bbox=({x1:.0f}, {y1:.0f}, {x2:.0f}, {y2:.0f})")

    result.save(filename="/Users/evnchn/ClaudeCodeCV/yolo_bus_result.jpg")
    print("\nAnnotated image saved to yolo_bus_result.jpg")
