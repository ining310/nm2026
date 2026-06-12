import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import AuthenticationError, OpenAI, RateLimitError

MODEL = "gpt-5.5"
PROMPT = """You are the AI vision module of a smart recycling bin.

Analyze the image of the garbage placed inside the detection area.

Your task is to classify the object into exactly one of the following categories:

1. metal_can
2. plastic_bottle
3. paper
4. glass
5. general_waste
6. unknown
7. multiple_categories

Rules:
- If there is clearly one recyclable object, classify it into the most suitable category.
- If the image contains multiple different objects, classify it as multiple_categories.
- If the object is dirty, mixed, broken, unclear, blocked, or hard to identify, classify it as unknown.
- If confidence is low, classify it as unknown.
- Only set recyclable = true when the object clearly belongs to one recyclable category.
- Only set single_category = true when there is exactly one object and one clear category.
- Do not guess if the object is unclear.

Return only JSON in the following format:

{
  "predicted_category": "metal_can | plastic_bottle | paper | glass | general_waste | unknown | multiple_categories",
  "target_bin": "Bin A | Bin B | Bin C | Bin D | manual_check",
  "confidence": 0.0,
  "recyclable": true,
  "single_category": true,
  "reward_eligible": true,
  "reason": "short explanation"
}

Bin mapping:
- metal_can → Bin A
- plastic_bottle → Bin B
- paper → Bin C
- glass → Bin D
- general_waste → manual_check
- unknown → manual_check
- multiple_categories → manual_check

Reward rule:
- reward_eligible = true only if recyclable = true, single_category = true, and confidence >= 0.80.
- Otherwise, reward_eligible = false.

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
