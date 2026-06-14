import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import AuthenticationError, OpenAI, RateLimitError

MODEL = "gpt-5.5"
PROMPT = """You are the AI vision module of a smart recycling bin.

Analyze the image of the garbage placed inside the detection area.
The object to be classified will be placed on a brown platform. Classify that object only — the brown platform and any background elements are not part of the classification.

Your task is to classify the object into exactly one of the following categories:

1. plastic  — any plastic item (bottles, bags, cups, utensils, containers, etc.)
2. metal    — any metal item (cans, foil, tins, etc.)
3. paper    — any paper item (newspapers, cardboard, paper cups, tissue boxes, etc.)
4. other    — anything that does not clearly fit the above three categories,
              including glass, food waste, mixed items, unclear or dirty objects

Rules:
- Classify into plastic, metal, or paper only if the object clearly belongs to that material.
- If the object is unclear, dirty, mixed, or could belong to multiple categories, classify as other.
- If confidence is low, classify as other.
- Only set recyclable = true for plastic, metal, or paper with a clear single object.
- Only set single_category = true when there is exactly one object and one clear category.
- Do not guess if the object is unclear.

Return only JSON in the following format:

{
  "predicted_category": "plastic | metal | paper | other",
  "target_bin": "Bin A | Bin B | Bin C | Bin D",
  "confidence": 0.0,
  "recyclable": true,
  "single_category": true,
  "reward_eligible": true,
  "reason": "short explanation"
}

Bin mapping:
- metal   → Bin A
- plastic → Bin B
- paper   → Bin C
- other   → Bin D

Reward rule:
- reward_eligible = true only if recyclable = true, single_category = true, and confidence >= 0.80.
- reward_eligible = false for other category or low confidence.

"""

DEFAULT_IMAGE = Path("captured.jpg")


def get_api_key() -> str:
    load_dotenv(override=True)
    api_key = (os.getenv("OPENAI_API_KEY") or "").strip()
    return api_key


def upload_image(client: OpenAI, image_path: Path) -> str:
    with image_path.open("rb") as image_file:
        result = client.files.create(file=image_file, purpose="vision")
    return result.id


def describe_image(client: OpenAI, image_path: Path, prompt: str = PROMPT) -> str:
    file_id = upload_image(client, image_path)

    response = client.responses.create(
        model=MODEL,
        input=[
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt},
                    {"type": "input_image", "file_id": file_id},
                ],
            }
        ],
    )
    return response.output_text


def main() -> None:
    parser = argparse.ArgumentParser(description="Ask OpenAI about an image.")
    parser.add_argument(
        "prompt",
        nargs="?",
        default=PROMPT,
    )
    parser.add_argument(
        "--image",
        default=str(DEFAULT_IMAGE),
        help=f"Path to the image file (default: {DEFAULT_IMAGE})",
    )
    args = parser.parse_args()

    image_path = Path(args.image)
    if not image_path.exists():
        print(f"Error: image not found at {image_path}")
        sys.exit(1)

    client = OpenAI(api_key=get_api_key())
    print(describe_image(client, image_path, prompt=args.prompt))


if __name__ == "__main__":
    main()
