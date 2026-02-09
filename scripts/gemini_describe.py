import base64
import os
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

ROOT = Path(__file__).parent.parent
OUTPUT = ROOT / "images" / "output"

load_dotenv(ROOT / ".env")

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_KEY"],
)


def encode_image(image_path: str) -> str:
    path = Path(image_path)
    mime_types = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}
    mime = mime_types.get(path.suffix.lower(), "image/png")
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    return f"data:{mime};base64,{b64}"


images = [
    (OUTPUT / "mysterious_no_bg.png", "Nyan Cat (background removed)"),
    (OUTPUT / "yolo_bus_result.jpg", "YOLO bus detection result"),
]

for filepath, label in images:
    filename = filepath.name
    print(f"\n{'='*60}")
    print(f"Image: {label} ({filename})")
    print(f"{'='*60}")

    data_uri = encode_image(filepath)

    completion = client.chat.completions.create(
        model="google/gemini-3-flash-preview",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Describe what you see in this image in detail."},
                    {"type": "image_url", "image_url": {"url": data_uri}},
                ],
            }
        ],
    )

    print(completion.choices[0].message.content)
