#!/usr/bin/env python3
import base64
import os
import re
from pathlib import Path

from openai import OpenAI

BASE = Path.cwd()
PROMPTS = BASE / "image_prompts.md"
OUT = BASE / "images"
MODEL = os.environ.get("OPENAI_IMAGE_MODEL", "gpt-image-2")
SIZE = os.environ.get("OPENAI_IMAGE_SIZE", "1536x864")


def load_env():
    for path in [BASE / ".env", BASE / ".evn"]:
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


def parse_prompts(text: str):
    pattern = re.compile(r"^## +(scene_[\w-]+|\d+[\w-]*)\s*$", re.M)
    matches = list(pattern.finditer(text))
    for i, match in enumerate(matches):
        name = match.group(1)
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        block = text[start:end].strip()
        code = re.search(r"```(?:text)?\s*(.*?)```", block, re.S)
        prompt = (code.group(1) if code else block).strip()
        if prompt and "ここに" not in prompt:
            yield name, prompt


def main():
    load_env()
    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY/API_KEY not found")
    if not PROMPTS.exists():
        raise SystemExit(f"Missing {PROMPTS}")

    OUT.mkdir(parents=True, exist_ok=True)
    client = OpenAI()
    for name, prompt in parse_prompts(PROMPTS.read_text(encoding="utf-8")):
        out = OUT / f"{name}.png"
        result = client.images.generate(
            model=MODEL,
            prompt=prompt,
            size=SIZE,
        )
        b64 = result.data[0].b64_json
        out.write_bytes(base64.b64decode(b64))
        print(out)


if __name__ == "__main__":
    main()
