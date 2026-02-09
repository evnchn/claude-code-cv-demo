"""Gemini 3 Flash: Structured image description via OpenRouter with enforced JSON schema."""

import base64
import json
import os
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_KEY"],
)

MODEL = "google/gemini-3-flash-preview"

# Enforced JSON schema
IMAGE_ANALYSIS_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "image_analysis",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "objects": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "label": {
                                "type": "string",
                                "description": "Short name for the detected object",
                            },
                            "description": {
                                "type": "string",
                                "description": "Detailed description of the object",
                            },
                        },
                        "required": ["label", "description"],
                        "additionalProperties": False,
                    },
                },
                "scene_description": {
                    "type": "string",
                    "description": "Overall description of the scene",
                },
            },
            "required": ["objects", "scene_description"],
            "additionalProperties": False,
        },
    },
}


def encode_image(image_path: str) -> str:
    path = Path(image_path)
    mime_types = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}
    mime = mime_types.get(path.suffix.lower(), "image/png")
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    return f"data:{mime};base64,{b64}"


images = [
    ("/Users/evnchn/ClaudeCodeCV/mysterious_no_bg.png", "Nyan Cat (background removed)"),
    ("/Users/evnchn/ClaudeCodeCV/yolo_bus_result.jpg", "YOLO bus detection result"),
]

for filepath, label in images:
    print(f"\n{'='*60}")
    print(f"Image: {label}")
    print(f"{'='*60}")

    data_uri = encode_image(filepath)

    completion = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Analyze this image. Identify all objects and describe the scene.",
                    },
                    {"type": "image_url", "image_url": {"url": data_uri}},
                ],
            }
        ],
        response_format=IMAGE_ANALYSIS_SCHEMA,
        extra_body={
            "provider": {"require_parameters": True},
        },
    )

    result = json.loads(completion.choices[0].message.content)
    print(json.dumps(result, indent=2))
