"""Gemini 3 Flash: Bounding box detection + visualization via OpenRouter."""

import base64
import json
import os
import random
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont

load_dotenv()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_KEY"],
)

MODEL = "google/gemini-3-flash-preview"

# Schema enforcing bounding box output
BBOX_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "bounding_boxes",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "detections": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "label": {
                                "type": "string",
                                "description": "Descriptive label for the detected object",
                            },
                            "box_2d": {
                                "type": "array",
                                "items": {"type": "integer"},
                                "description": "[ymin, xmin, ymax, xmax] normalized 0-1000",
                            },
                        },
                        "required": ["label", "box_2d"],
                        "additionalProperties": False,
                    },
                }
            },
            "required": ["detections"],
            "additionalProperties": False,
        },
    },
}

DETECTION_PROMPT = (
    "Detect all prominent objects in this image. "
    'Return bounding boxes in the key "box_2d" as [ymin, xmin, ymax, xmax] '
    'normalized to 0-1000, and a descriptive label in the key "label".'
)


def encode_image(image_path: str) -> str:
    path = Path(image_path)
    mime_types = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}
    mime = mime_types.get(path.suffix.lower(), "image/png")
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    return f"data:{mime};base64,{b64}"


def detect_objects(image_path: str) -> list:
    data_uri = encode_image(image_path)
    completion = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": DETECTION_PROMPT},
                    {"type": "image_url", "image_url": {"url": data_uri}},
                ],
            }
        ],
        response_format=BBOX_SCHEMA,
        extra_body={
            "provider": {"require_parameters": True},
        },
        temperature=0.0,
    )
    result = json.loads(completion.choices[0].message.content)
    return result["detections"]


def draw_bounding_boxes(image_path: str, detections: list, output_path: str):
    img = Image.open(image_path).convert("RGB")
    draw = ImageDraw.Draw(img)
    img_width, img_height = img.size

    # Try to load a decent font
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 16)
    except OSError:
        font = ImageFont.load_default()

    # Distinct colors per detection
    random.seed(42)
    colors = [
        (random.randint(80, 255), random.randint(80, 255), random.randint(80, 255))
        for _ in range(max(len(detections), 1))
    ]

    for det, color in zip(detections, colors):
        label = det["label"]
        ymin, xmin, ymax, xmax = det["box_2d"]

        # Convert normalized [0-1000] to pixel coords
        left = (xmin / 1000) * img_width
        top = (ymin / 1000) * img_height
        right = (xmax / 1000) * img_width
        bottom = (ymax / 1000) * img_height

        # Draw rectangle (3px border)
        for i in range(3):
            draw.rectangle([left - i, top - i, right + i, bottom + i], outline=color)

        # Draw label
        text_bbox = draw.textbbox((0, 0), label, font=font)
        text_w = text_bbox[2] - text_bbox[0]
        text_h = text_bbox[3] - text_bbox[1]
        label_y = top - text_h - 6 if top - text_h - 6 > 0 else top + 4
        draw.rectangle([left, label_y, left + text_w + 8, label_y + text_h + 6], fill=color)
        draw.text((left + 4, label_y + 2), label, fill="white", font=font)

    img.save(output_path, quality=95)
    print(f"  Saved annotated image to {output_path}")


# Run on both images
images = [
    ("/Users/evnchn/ClaudeCodeCV/mysterious_no_bg.png", "gemini_bbox_nyancat.png"),
    ("/Users/evnchn/ClaudeCodeCV/bus.jpg", "gemini_bbox_bus.jpg"),
]

for image_path, output_name in images:
    output_path = f"/Users/evnchn/ClaudeCodeCV/{output_name}"
    print(f"\n{'='*60}")
    print(f"Detecting objects in: {Path(image_path).name}")
    print(f"{'='*60}")

    detections = detect_objects(image_path)
    print(f"  Found {len(detections)} objects:")
    for det in detections:
        print(f"    {det['label']:35s} box_2d={det['box_2d']}")

    draw_bounding_boxes(image_path, detections, output_path)
