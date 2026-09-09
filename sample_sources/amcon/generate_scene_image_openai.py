#!/usr/bin/env python3
import argparse
import base64
import json
import os
import re
from pathlib import Path

from openai import OpenAI

ROOT = Path(__file__).resolve().parents[1]
ENV_ROOT = ROOT.parent / "video_samples"
OUT = ROOT / "scenes" / "images"
LOGS = ROOT / "logs"
MODEL = "gpt-image-2"
USD_JPY = 160

RATES_PER_1M = {
    "text_input_tokens": 5.00,
    "image_input_tokens": 8.00,
    "output_tokens": 30.00,
}

V2_VISUAL_DIRECTION = """

V2 revision direction from client feedback:
- Strengthen the documentary feeling: more grounded, cinematic, professional, sincere, less cute.
- Characters must look Mexican / Latino, with natural Latin American facial features and warm medium skin tones.
- Avoid Japanese, East Asian, Korean, or generic anime-idol facial impressions for Benjamin, Jose Luis, customers, engineers, managers, and team members.
- Keep the warm Showa-era anime inspired illustration style, but make facial structures and body language fit Mexican professionals.
- The final third should feel grand and emotionally uplifting, with larger scale, stronger light, and documentary achievement mood.
""".strip()


SCENES = {
    "01": {
        "output": "scene_01_mexico_treatment_plant_intro.png",
        "images": [
            ROOT / "reference" / "volute" / "article_main_11.jpg",
            ROOT / "reference" / "volute" / "volute_duo_product.png",
        ],
        "prompt": """
Create scene_01 for an internal corporate story video.

Scene: a wide establishing shot of a large wastewater treatment plant in Mexico at sunrise. There are circular treatment tanks, water channels, pipes, walkways, industrial buildings, distant mountains, and warm morning light. The mood is quiet, sincere, hopeful, and professional.

Visual direction: this is the opening title-card background. Leave generous open sky and clean empty space in the upper-left area for a title overlay that will be added later. Do not include any text now.

Style: original warm Japanese Showa-era anime inspired corporate illustration, gentle and sincere tone, clean linework, soft cel-shading, professional internal company event video style. Slightly energetic and hopeful, but not a copy of any existing anime franchise. No existing anime characters, no franchise references.

Composition: 16:9 landscape, cinematic wide view, subtitle safe space near the bottom. No text, no logos, no watermarks, no readable signage.
""".strip(),
    },
    "02": {
        "output": "scene_02_exhibition_meets_volute.png",
        "images": [
            ROOT / "characters" / "illustrations" / "benjamin_showa_anime_portrait.png",
            ROOT / "reference" / "volute" / "volute_duo_product.png",
            ROOT / "reference" / "volute" / "volute_filter_body.jpg",
        ],
        "prompt": """
Create scene_02 for an internal corporate story video.

Scene: an international water-treatment technology exhibition. Benjamin, based on the provided character reference, stands at a booth and sees the VOLUTE sludge dewatering machine for the first time. He looks impressed and thoughtful, holding a brochure, as if realizing the machine's potential.

Character direction: keep Benjamin consistent with the reference portrait: Mexican man, short neatly combed black hair, rectangular black glasses, friendly but serious expression, professional shirt. Do not make him a different person.

Machine direction: draw an industrial sludge dewatering machine inspired by AMCON VOLUTE. It should have a long horizontal metallic cylindrical filtering body made of many stacked rings, with a screw shaft running through the center, motor and gearbox at one end, hopper, pipes, support frame and legs. It must look closer to the provided VOLUTE references than to a conveyor belt, centrifuge, washing machine, or generic tank. Do not draw logos or readable text.

Visual style: original warm Japanese Showa-era anime inspired corporate illustration, gentle and sincere tone, clean linework, soft cel-shading, professional internal company event video style. Slightly energetic and hopeful, but not a copy of any existing anime franchise. No existing anime characters, no franchise references.

Composition: 16:9 landscape, Benjamin on the left third looking toward the machine on the right, exhibition visitors softly in the background, clean booth lighting. Leave safe space at the bottom for subtitles. No text, no logos, no watermarks, no readable signage.
""".strip(),
    },
    "03": {
        "output": "scene_03_volute_mechanism.png",
        "images": [
            ROOT / "reference" / "volute" / "volute_filter_body.jpg",
            ROOT / "reference" / "volute" / "dewatering_cake.png",
        ],
        "prompt": """
Create scene_03 for an internal corporate story video.

Scene: a clear technical cutaway illustration of the VOLUTE sludge dewatering mechanism. Show a long horizontal metallic cylindrical filtering body made of many stacked rings, with a screw shaft running through the center. Sludge enters from a hopper, water separates and drains downward, and dewatered sludge cake exits from the end.

Important machine direction: it must look like a multi-disc screw press sludge dewatering machine, not a belt conveyor, centrifuge, washing machine, or generic tank. Emphasize stacked rings, screw shaft, motor, frame, and sludge cake discharge.

Visual style: original warm Japanese Showa-era anime inspired corporate illustration with a clean technical feeling, soft cel-shading, no text labels. Use arrows only if they are abstract and unlabelled; no readable words.

Composition: 16:9 landscape, machine centered, clean background, subtitle safe space near the bottom. No text, no logos, no watermarks, no readable signage.
""".strip(),
    },
    "04": {
        "output": "scene_04_sales_across_mexico.png",
        "images": [
            ROOT / "characters" / "illustrations" / "benjamin_showa_anime_portrait.png",
            ROOT / "reference" / "volute" / "volute_duo_product.png",
        ],
        "prompt": """
Create scene_04 for an internal corporate story video.

Scene: Benjamin actively conducts sales across Mexico. He stands in the foreground holding product materials, looking determined and approachable. Behind him is a montage-like background: a subtle map silhouette of Mexico, factories, water-treatment sites, a road, and small vignettes of him meeting customers.

Character direction: keep Benjamin consistent with the reference portrait: Mexican man, short neatly combed black hair, rectangular black glasses, friendly serious expression, professional shirt.

Machine direction: product materials may show a small simplified industrial sludge dewatering machine inspired by VOLUTE: long horizontal metallic cylindrical filtering body with stacked rings and a screw shaft. No logos or readable text.

Visual style: original warm Japanese Showa-era anime inspired corporate illustration, gentle and sincere, clean linework, soft cel-shading, professional internal company event video style, hopeful and energetic without copying any franchise.

Composition: 16:9 landscape, Benjamin foreground left or center, montage background, subtitle safe space near bottom. No text, no logos, no watermarks, no readable signage.
""".strip(),
    },
    "05": {
        "output": "scene_05_conflict_at_previous_company.png",
        "images": [
            ROOT / "characters" / "illustrations" / "benjamin_showa_anime_portrait.png",
            ROOT / "reference" / "volute" / "volute_duo_product.png",
        ],
        "prompt": """
Create scene_05 for an internal corporate story video.

Scene: a tense but professional meeting room at Benjamin's previous water-treatment company. A manager presents a cheaper alternative product direction, while Benjamin respectfully but firmly pushes back because he believes customers should receive the original Japanese-made VOLUTE. Show contrast through body language and documents, without readable text.

Character direction: keep Benjamin consistent with the reference portrait: Mexican man, short neatly combed black hair, rectangular black glasses, sincere and determined expression. The manager should be older, serious, but not villainous.

Machine direction: one document on the table may show a simplified VOLUTE-like sludge dewatering machine, with a long metallic cylindrical filtering body and screw shaft. Do not include logos or readable product names in the image.

Visual style: original warm Japanese Showa-era anime inspired corporate illustration, corporate drama tone, clean linework, soft cel-shading, professional internal company event video style. No franchise references.

Composition: 16:9 landscape, meeting table, Benjamin on one side, manager on the other, subtitle safe space near bottom. No text, no logos, no watermarks, no readable signage.
""".strip(),
    },
    "06": {
        "output": "scene_06_decision_to_start_company.png",
        "images": [
            ROOT / "characters" / "illustrations" / "benjamin_showa_anime_portrait.png",
            ROOT / "reference" / "volute" / "volute_filter_body.jpg",
        ],
        "prompt": """
Create scene_06 for an internal corporate story video.

Scene: nighttime office. Benjamin sits alone at a desk, deciding to leave the company and start his own business to sell VOLUTE. Warm desk lamp, city lights outside the window, notebook, pen, coffee, and product reference materials on the desk.

Character direction: keep Benjamin consistent with the reference portrait: Mexican man, short neatly combed black hair, rectangular black glasses. His expression should be serious, resolved, and hopeful.

Machine direction: product reference materials on the desk may include a small image of a VOLUTE-like multi-disc screw press, but no readable text or logos.

Visual style: original warm Japanese Showa-era anime inspired corporate illustration, gentle sincere tone, clean linework, soft cel-shading, dramatic warm lighting. No franchise references.

Composition: 16:9 landscape, Benjamin at desk, strong emotional focus, subtitle safe space near bottom. No text, no logos, no watermarks, no readable signage.
""".strip(),
    },
    "07": {
        "output": "scene_07_startup_with_little_money.png",
        "images": [
            ROOT / "characters" / "illustrations" / "benjamin_showa_anime_portrait.png",
            ROOT / "reference" / "volute" / "volute_duo_product.png",
        ],
        "prompt": """
Create scene_07 for an internal corporate story video.

Scene: Benjamin prepares to start his business in a small modest room. On the desk are an old laptop, handwritten business notes, a small amount of cash, a calculator, and product brochures. The room is humble but filled with determination.

Character direction: keep Benjamin consistent with the reference portrait: Mexican man, short neatly combed black hair, rectangular black glasses, sincere and determined expression.

Machine direction: brochures can contain simplified product photos of a VOLUTE-like sludge dewatering machine, but no readable text or logos.

Visual style: original warm Japanese Showa-era anime inspired corporate illustration, gentle and sincere tone, clean linework, soft cel-shading, internal company story video. No franchise references.

Composition: 16:9 landscape, desk and Benjamin in focus, subtitle safe space near bottom. No text, no logos, no watermarks, no readable signage.
""".strip(),
    },
    "08": {
        "output": "scene_08_old_pickup_truck.png",
        "images": [
            ROOT / "characters" / "illustrations" / "benjamin_showa_anime_portrait.png",
        ],
        "prompt": """
Create scene_08 for an internal corporate story video.

Scene: Benjamin stands in a used-car lot in Mexico, looking at an old white pickup truck that will become his work partner. The truck is practical and worn, with small scratches and a bit of rust, but it feels dependable. Mountains and blue sky in the background.

Character direction: keep Benjamin consistent with the reference portrait: Mexican man, short neatly combed black hair, rectangular black glasses, professional shirt, thoughtful hopeful expression.

Visual style: original warm Japanese Showa-era anime inspired corporate illustration, gentle and sincere tone, clean linework, soft cel-shading, a subtle energetic adventure feeling without copying any existing anime franchise.

Composition: 16:9 landscape, truck prominent, Benjamin beside it, subtitle safe space near bottom. Do not include price signs, text, logos, watermarks, or readable signage.
""".strip(),
    },
    "09": {
        "output": "scene_09_truck_with_demo_unit.png",
        "images": [
            ROOT / "characters" / "illustrations" / "benjamin_showa_anime_portrait.png",
            ROOT / "reference" / "volute" / "volute_filter_body.jpg",
            ROOT / "reference" / "volute" / "volute_duo_product.png",
        ],
        "prompt": """
Create scene_09 for an internal corporate story video.

Scene: an old pickup truck is driving normally on a paved or dry rural Mexican road through mountains and open sky. The vehicle must be physically coherent and believable, with all four wheels on the road, correct perspective, and no impossible off-road position. In the truck bed is a compact demo unit inspired by the VOLUTE sludge dewatering machine, securely strapped down with straps.

Character direction: Benjamin must be clearly seated inside the driver's seat, visible through the windshield or side window, hands on the steering wheel, looking forward and driving safely. Keep him consistent with the reference portrait: Mexican man, short neatly combed black hair, rectangular black glasses. Do not place Benjamin standing outside the truck for this scene. Do not put his head floating above the cab. Do not put him in the truck bed.

Machine direction: the demo unit must clearly show a long horizontal metallic cylindrical filtering body with stacked rings, a screw shaft impression, motor, and support frame. It should not look like a generic tank or generator. No logos or readable text.

Visual style: original warm Japanese Showa-era anime inspired corporate illustration, hopeful, energetic, sincere, clean linework, soft cel-shading. Avoid franchise references.

Composition: 16:9 landscape, three-quarter front or side view of the truck, road motion, driver visible in the cab, truck bed and demo unit clear, subtitle safe space near bottom. No text, no logos, no watermarks, no readable signage.
""".strip(),
    },
    "10": {
        "output": "scene_10_customer_demo.png",
        "images": [
            ROOT / "characters" / "illustrations" / "benjamin_showa_anime_portrait.png",
            ROOT / "reference" / "volute" / "volute_filter_body.jpg",
            ROOT / "reference" / "volute" / "dewatering_cake.png",
        ],
        "prompt": """
Create scene_10 for an internal corporate story video.

Scene: Benjamin demonstrates a VOLUTE-like sludge dewatering demo machine at an industrial customer site. Factory workers and customer representatives watch the process and inspect the dewatered sludge cake. The customers look impressed and convinced.

Character direction: keep Benjamin consistent with the reference portrait: Mexican man, short neatly combed black hair, rectangular black glasses, professional and confident.

Machine direction: draw an industrial sludge dewatering machine with a long horizontal metallic cylindrical filtering body made of stacked rings, screw shaft, motor, hopper, pipes, support frame, water draining downward, and sludge cake discharged from the end. Use the dewatered cake reference.

Separation clarity is critical: the separated dewatered sludge cake and the filtrate water must go into clearly different places. The sludge cake should discharge from the end into a dry-looking separate bin or tray on one side. The filtrate water should drain downward into a different small collection tray, gutter, bucket, or transparent hose leading to a separate water container. Do not put water into the sludge cake bin. Do not show the filtrate water and sludge cake mixing together. The scene should clearly communicate separation: solid cake here, clarified water there.

No one should touch sludge by hand. People may observe it from a short distance, point at it with a gloved hand or pen, or look impressed while keeping clean professional posture. No logos or readable text.

Visual style: original warm Japanese Showa-era anime inspired corporate illustration, sincere corporate documentary feeling, clean linework, soft cel-shading. No franchise references.

Composition: 16:9 landscape, machine and people both visible, subtitle safe space near bottom. No text, no logos, no watermarks, no readable signage.
""".strip(),
    },
    "11": {
        "output": "scene_11_jose_luis_support.png",
        "images": [
            ROOT / "characters" / "illustrations" / "benjamin_showa_anime_portrait.png",
            ROOT / "characters" / "illustrations" / "jose_luis_showa_anime_portrait.png",
            ROOT / "reference" / "volute" / "volute_duo_product.png",
        ],
        "prompt": """
Create scene_11 for an internal corporate story video.

Scene: a small office at night. Benjamin and Jose Luis sit side by side reviewing a laptop, a Mexico map, and product materials. They look like close friends and business partners making a plan together. Warm desk light, focused but hopeful mood.

Character direction: keep Benjamin consistent with his reference portrait: Mexican man, short neatly combed black hair, rectangular black glasses. Keep Jose Luis consistent with his reference portrait: Mexican man, short black hair, white shirt, friendly reliable expression.

Machine direction: a small model or product photo of a VOLUTE-like sludge dewatering machine can be on the desk, but no readable text or logos.

Visual style: original warm Japanese Showa-era anime inspired corporate illustration, gentle and sincere, clean linework, soft cel-shading, internal company story video. No franchise references.

Composition: 16:9 landscape, both men clearly visible, warm office, subtitle safe space near bottom. No text, no logos, no watermarks, no readable signage.
""".strip(),
    },
    "12": {
        "output": "scene_12_pandemic_never_give_up.png",
        "images": [
            ROOT / "characters" / "illustrations" / "benjamin_showa_anime_portrait.png",
            ROOT / "characters" / "illustrations" / "jose_luis_showa_anime_portrait.png",
        ],
        "prompt": """
Create scene_12 for an internal corporate story video.

Scene: the pandemic period. Benjamin and Jose Luis continue working despite uncertainty. Show them wearing masks in a small office with an online meeting on a laptop, and in the background a quiet street or closed factory gate. The mood is difficult but not hopeless; they are determined not to give up.

Character direction: keep Benjamin consistent with his reference portrait, including rectangular glasses. Keep Jose Luis consistent with his reference portrait, short black hair and reliable expression.

Visual style: original warm Japanese Showa-era anime inspired corporate illustration, sincere corporate story tone, clean linework, soft cel-shading, restrained drama. No franchise references.

Composition: 16:9 landscape, two men and laptop in foreground, pandemic context in background, subtitle safe space near bottom. No readable text on the laptop, no logos, no watermarks, no readable signage.
""".strip(),
    },
    "13": {
        "output": "scene_13_large_order_success.png",
        "images": [
            ROOT / "characters" / "illustrations" / "benjamin_showa_anime_portrait.png",
            ROOT / "reference" / "volute" / "volute_duo_product.png",
            ROOT / "reference" / "volute" / "volute_filter_body.jpg",
        ],
        "prompt": """
Create scene_13 for an internal corporate story video.

Scene: the moment a major order is won. In a corporate meeting room or industrial facility, Benjamin shakes hands with a customer decision-maker while colleagues applaud. A large VOLUTE-like sludge dewatering machine stands in the background, representing the HR-802 order. The feeling is restrained but triumphant.

Character direction: keep Benjamin consistent with the reference portrait: Mexican man, short neatly combed black hair, rectangular black glasses, confident and grateful expression.

Machine direction: large multi-disc screw press sludge dewatering machine, long metallic cylindrical filtering body made of stacked rings, screw shaft, motor, hopper, pipes, frame and legs. It must not look like a belt conveyor or centrifuge. No logos or readable product names.

Visual style: original warm Japanese Showa-era anime inspired corporate illustration, professional corporate documentary feeling, clean linework, soft cel-shading, hopeful achievement. No franchise references.

Composition: 16:9 landscape, handshake foreground, large machine background, subtitle safe space near bottom. No text, no logos, no watermarks, no readable signage.
""".strip(),
    },
    "13b": {
        "output": "scene_13b_san_antonio_project_explanation.png",
        "images": [
            ROOT / "scenes" / "images" / "scene_13_large_order_success.png",
            ROOT / "reference" / "volute" / "article_main_11.jpg",
            ROOT / "reference" / "volute" / "volute_duo_product.png",
            ROOT / "reference" / "volute" / "volute_filter_body.jpg",
        ],
        "prompt": """
Create scene_13b for an internal corporate story video.

Scene: a clear explanatory establishing shot of the huge San Antonio wastewater treatment project. Show a massive newly built wastewater treatment plant on a mountain or highland site, with circular treatment tanks, water channels, pipes, industrial buildings, construction roads, and engineers observing the facility from a safe overlook. The scene should communicate that this is an exceptionally large Mexico-United States joint infrastructure project, without using readable text.

Project direction: include a subtle international-collaboration feeling through two groups of professional engineers and government-style project staff reviewing plans together, one group with a Mexican flag-colored folder or small non-readable flag color accent, another with a United States flag-colored folder or small non-readable flag color accent. Do not draw actual readable flags, national seals, logos, slogans, or text.

Machine direction: include several VOLUTE-like sludge dewatering machines integrated into the plant area, inspired by the provided references. They should have long horizontal metallic cylindrical filtering bodies made of stacked rings, screw shafts, motors, frames, and pipes. They must not look like belt conveyors, centrifuges, washing machines, or generic tanks.

Visual style: match the existing scene_13 illustration style: original warm Japanese Showa-era anime inspired corporate illustration, gentle and sincere tone, clean linework, soft cel-shading, professional internal company event video style. No existing anime characters, no franchise references.

Composition: 16:9 landscape, cinematic wide view. Plant scale should be immediately understandable. Put engineers in the foreground or lower side as small human scale references, with the huge treatment plant behind them. Leave subtitle safe space near the bottom. No text, no logos, no watermarks, no readable signage.
""".strip(),
    },
    "14": {
        "output": "scene_14_san_antonio_future_team.png",
        "images": [
            ROOT / "characters" / "illustrations" / "benjamin_showa_anime_portrait.png",
            ROOT / "characters" / "illustrations" / "jose_luis_showa_anime_portrait.png",
            ROOT / "reference" / "volute" / "volute_duo_product.png",
        ],
        "prompt": """
Create scene_14 for an internal corporate story video.

Scene: final hopeful team shot at a huge wastewater treatment plant inspired by the San Antonio project. Benjamin, Jose Luis, and a grown team of about ten people stand proudly but naturally in front of circular treatment tanks, pipes, industrial buildings, and several VOLUTE-like sludge dewatering machines. Wide open sky, bright future feeling.

Character direction: keep Benjamin consistent with his reference portrait: Mexican man, short neatly combed black hair, rectangular black glasses. Keep Jose Luis consistent with his reference portrait: short black hair, reliable friendly expression. Other team members should look like diverse professional staff.

Machine direction: multiple industrial sludge dewatering machines inspired by VOLUTE, with long horizontal metallic cylindrical filtering bodies, stacked rings, motors, frames, pipes. No logos or readable product names.

Visual style: original warm Japanese Showa-era anime inspired corporate illustration, gentle and sincere, clean linework, soft cel-shading, professional internal company event video style, bright achievement and future-oriented mood. No franchise references.

Composition: 16:9 landscape, team foreground, large treatment plant and machines background, subtitle safe space near bottom. No text, no logos, no watermarks, no readable signage.
""".strip(),
    },
}


def load_env():
    for env_name in [".env", ".evn"]:
        path = ENV_ROOT / env_name
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
    details = data.get("input_tokens_details", {})
    output_details = data.get("output_tokens_details", {})
    text_input = data.get("text_input_tokens") or details.get("text_tokens") or 0
    image_input = data.get("image_input_tokens") or details.get("image_tokens") or 0
    output = data.get("output_tokens") or data.get("image_output_tokens") or output_details.get("image_tokens") or 0
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("scene_id")
    args = parser.parse_args()
    scene_id = args.scene_id.zfill(2)
    if scene_id not in SCENES:
        raise SystemExit(f"Unknown scene: {scene_id}")

    load_env()
    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY/API_KEY not found")

    OUT.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)

    scene = SCENES[scene_id]
    client = OpenAI()
    image_files = [p.open("rb") for p in scene["images"]]
    try:
        result = client.images.edit(
            model=MODEL,
            image=image_files,
            prompt=f"{scene['prompt']}\n\n{V2_VISUAL_DIRECTION}",
            size="1536x1024",
        )
    finally:
        for f in image_files:
            f.close()

    out_file = OUT / scene["output"]
    out_file.write_bytes(base64.b64decode(result.data[0].b64_json))

    usage = getattr(result, "usage", None)
    log = {
        "scene_id": scene_id,
        "model": MODEL,
        "output": str(out_file),
        "input_images": [str(p) for p in scene["images"]],
        "usage": usage.to_dict() if hasattr(usage, "to_dict") else usage,
        "estimated_cost": usage_to_cost(usage),
    }
    (LOGS / f"scene_{scene_id}_api_usage.json").write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(log, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
