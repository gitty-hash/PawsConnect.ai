"""Bonus (Part B): generate a promotional banner for ONE pet with an image-generation model.

Mirrors Shopify Magic from Chapter 2 (a diffusion-style model turns a product photo into a
marketing visual). The course labs use Stable Diffusion (SD-Turbo); here the OpenAI image
model is used instead - an outside tool, disclosed in the report.

    python scripts/generate_banner.py            # needs OPENAI_API_KEY

Output: data/banners/cocoa_banner.png and data/banners/banner_meta.json (tool, prompt, date).
The banner is a DRAFT: staff must approve it before it is posted, and the app labels it
"AI-generated".
"""
from __future__ import annotations

import base64
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pawsconnect.llm import LLMGateway  # noqa: E402

PET = "Cocoa"
PHOTO = ROOT / "Testing_Images" / "dog_01.jpg"
OUT_DIR = ROOT / "data" / "banners"
MODEL = "gpt-image-1"
SIZE, QUALITY = "1536x1024", "medium"

PROMPT = (
    "Create a warm, friendly adoption banner in a clean flat-illustration style for a shelter dog named "
    f"{PET}. Use the provided photo for the dog's look: a chocolate-brown Labrador-type dog looking up with "
    "an open, happy mouth. Landscape layout with the dog on the left and open space on the right. Soft warm "
    "colours (cream, terracotta, sage green), a few subtle paw-print shapes, a simple park background. "
    f"Headline text exactly: 'Meet {PET}'. Smaller line exactly: 'Adopt me through PawsConnect'. "
    "Spell the text exactly as given and add no other words. Do not add any other animals or people, and do not "
    "make any claims about the dog's behaviour."
)


def main() -> None:
    client = LLMGateway("live")._get_client()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with PHOTO.open("rb") as f:
        resp = client.images.edit(model=MODEL, image=f, prompt=PROMPT, size=SIZE, quality=QUALITY, n=1)
    img_bytes = base64.b64decode(resp.data[0].b64_json)
    out = OUT_DIR / "cocoa_banner.png"
    out.write_bytes(img_bytes)
    meta = {
        "pet": PET, "tool": f"OpenAI Images API ({MODEL}, images.edit)", "source_photo": "Testing_Images/dog_01.jpg (CC0)",
        "size": SIZE, "quality": QUALITY, "prompt": PROMPT, "generated": time.strftime("%Y-%m-%d"),
        "usage": getattr(resp, "usage", None) and json.loads(resp.usage.model_dump_json()),
        "note": "AI-generated draft; staff approval required before posting.",
    }
    (OUT_DIR / "banner_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print("wrote", out, f"({len(img_bytes) // 1024} KB)")
    print("usage:", meta["usage"])


if __name__ == "__main__":
    main()
