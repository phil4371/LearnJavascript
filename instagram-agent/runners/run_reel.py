#!/usr/bin/env python3
"""Erstellt und postet ein Reel für den angegebenen Account."""
import sys
import random
import tempfile
import requests
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import load_account_config, parse_args
from modules.state_manager import StateManager
from modules.image_generator import ImageGenerator
from modules.caption_writer import CaptionWriter
from modules.reel_creator import ReelCreator
from modules.instagram_publisher import InstagramPublisher

BASE_DIR = Path(__file__).parent.parent
ASSETS_DIR = BASE_DIR / "assets"


def main():
    args = parse_args()
    cfg = load_account_config(args.account)

    state = StateManager(cfg["account_dir"])
    item = state.get_next_queued_post("reel")
    if not item:
        print(f"[{args.account}] Kein Reel in der Queue.")
        return

    topic = item["topic"]
    pillar = item["pillar"]
    affiliate_cta = bool(item["affiliate_cta"])

    print(f"[{args.account}] Reel: {topic}")

    img_gen = ImageGenerator(cfg)
    cap_writer = CaptionWriter(cfg)
    reel_creator = ReelCreator(ASSETS_DIR)

    # 4 Bilder generieren
    image_prompts = [
        f"Instagram Reel Frame {i+1}/4 zum Thema: {topic}. "
        f"9:16 Format. Slide {i+1} einer animierten Präsentation. "
        f"Nische: {cfg['pillars'].get('niche_name', '')}."
        for i in range(4)
    ]

    image_paths = []
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        for i, prompt in enumerate(image_prompts):
            url = img_gen.generate_and_upload(prompt, size="9:16")
            img_path = tmp / f"frame_{i}.jpg"
            r = requests.get(url, timeout=30)
            r.raise_for_status()
            img_path.write_bytes(r.content)
            image_paths.append(img_path)
            print(f"[{args.account}] Frame {i+1}/4 generiert")

        # Musik auswählen
        music_files = list(ASSETS_DIR.glob("music/*.mp3"))
        music = random.choice(music_files) if music_files else None

        # Reel rendern
        output_path = tmp / "reel.mp4"
        cta_text = cfg["pillars"].get("affiliate_ctas", {}).get("default", "Link in Bio 👆")
        reel_creator.create(image_paths, output_path, title=topic[:50], cta=cta_text, music_file=music)
        print(f"[{args.account}] Reel gerendert: {output_path.stat().st_size // 1024} KB")

        caption = cap_writer.write_caption(topic, "reel", pillar, affiliate_cta)

        if args.dry_run:
            print(f"[{args.account}] Dry-Run — kein echter Post.")
            return

        # Video zu imgbb hochladen (als URL für Meta-API)
        video_url = img_gen._upload_imgbb(output_path.read_bytes())

        publisher = InstagramPublisher(cfg["ig_access_token"], cfg["ig_account_id"])
        media_id = publisher.post_reel(video_url, caption)
        print(f"[{args.account}] Reel gepostet: {media_id}")

    state.mark_queue_item_done(item["id"], media_id)
    state.mark_topic_used(topic)


if __name__ == "__main__":
    main()
