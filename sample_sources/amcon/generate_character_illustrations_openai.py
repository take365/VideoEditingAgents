#!/usr/bin/env python3
import base64
import json
import os
from pathlib import Path

from openai import OpenAI

BASE = Path(__file__).resolve().parents[2] / "video_samples"
HERE = Path(__file__).resolve().parent
OUT = HERE / "illustrations"
LOGS = Path(__file__).resolve().parents[1] / "logs"

MODEL = "gpt-image-2"
USD_JPY = 160

# Official OpenAI pricing page checked 2026-05-15:
# GPT-Image-2 image input $8/M tokens, image output $30/M tokens, text input $5/M tokens.
RATES_PER_1M = {
    "text_input_tokens": 5.00,
    "image_input_tokens": 8.00,
    "output_tokens": 30.00,
}


def load_env():
    for env_name in [".env", ".evn"]:
        path = BASE / env_name
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip() or line.lstrip().startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and value and key not in os.environ:
                os.environ[key] = value
    if not os.environ.get("OPENAI_API_KEY") and os.environ.get("API_KEY"):
        os.environ["OPENAI_API_KEY"] = os.environ["API_KEY"]


def usage_to_cost(usage):
    if not usage:
        return None
    data = usage.to_dict() if hasattr(usage, "to_dict") else dict(usage)
    text_input = data.get("text_input_tokens") or data.get("input_tokens_details", {}).get("text_tokens") or 0
    image_input = data.get("image_input_tokens") or data.get("input_tokens_details", {}).get("image_tokens") or 0
    output = data.get("output_tokens") or data.get("image_output_tokens") or 0
    usd = (
        text_input * RATES_PER_1M["text_input_tokens"]
        + image_input * RATES_PER_1M["image_input_tokens"]
        + output * RATES_PER_1M["output_tokens"]
    ) / 1_000_000
    return {
        "text_input_tokens": text_input,
        "image_input_tokens": image_input,
        "output_tokens": output,
        "usd": usd,
        "jpy_at_160": usd * USD_JPY,
    }


def generate(client, name, source, output):
    prompt = f"""
Create an original character illustration based on the provided reference photo.

Character: {name}
Goal: A clean, friendly internal corporate video character portrait.
Style: warm Japanese Showa-era TV anime inspired illustration, soft linework, gentle expression, professional and approachable, not a copy of any existing anime franchise or character.
Composition: upper-body portrait, facing camera, neutral simple background, suitable for later use in a story video.
Important: preserve the person's broad facial impression, hairstyle, glasses if present, age impression, and friendly expression.
Ethnicity and face direction: this person is Mexican / Latino. Keep a distinctly Mexican / Latin American facial impression, warm medium skin tone, natural facial structure, and professional local-Mexican atmosphere. Avoid making the face look Japanese, East Asian, Korean, or generic anime-idol-like.
Do not include logos, text, watermarks, or readable signage.
""".strip()

    with source.open("rb") as image_file:
        result = client.images.edit(
            model=MODEL,
            image=[image_file],
            prompt=prompt,
            size="1024x1024",
        )

    output.write_bytes(base64.b64decode(result.data[0].b64_json))
    usage = getattr(result, "usage", None)
    return {
        "name": name,
        "model": MODEL,
        "source": str(source),
        "output": str(output),
        "usage": usage.to_dict() if hasattr(usage, "to_dict") else usage,
        "estimated_cost": usage_to_cost(usage),
    }


def main():
    load_env()
    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY/API_KEY not found")

    OUT.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    client = OpenAI()

    jobs = [
        (
            "Benjamin",
            HERE / "source_crops" / "benjamin_reference_crop.jpg",
            OUT / "benjamin_showa_anime_portrait.png",
        ),
        (
            "Jose Luis",
            HERE / "source_crops" / "jose_luis_reference_crop.jpg",
            OUT / "jose_luis_showa_anime_portrait.png",
        ),
    ]

    logs = [generate(client, *job) for job in jobs]
    (LOGS / "character_illustration_api_usage.json").write_text(
        json.dumps(logs, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(logs, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
