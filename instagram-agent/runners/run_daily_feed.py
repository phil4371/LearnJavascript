#!/usr/bin/env python3
"""Postet den nächsten geplanten Feed-Beitrag für den angegebenen Account."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import load_account_config, parse_args
from modules.state_manager import StateManager
from modules.image_generator import ImageGenerator
from modules.caption_writer import CaptionWriter
from modules.instagram_publisher import InstagramPublisher


def main():
    args = parse_args()
    cfg = load_account_config(args.account)

    state = StateManager(cfg["account_dir"])
    item = state.get_next_queued_post("feed")
    if not item:
        print(f"[{args.account}] Keine Feed-Posts in der Queue — Wochenplaner ausführen.")
        return

    topic = item["topic"]
    pillar = item["pillar"]
    affiliate_cta = bool(item["affiliate_cta"])

    print(f"[{args.account}] Feed-Post: {topic}")

    img_gen = ImageGenerator(cfg)
    cap_writer = CaptionWriter(cfg)

    # Bild generieren
    image_prompt = (
        f"Instagram-Infografik zum Thema: {topic}. "
        f"Nische: {cfg['pillars'].get('niche_name', '')}. "
        f"Keine Personen, keine Logos. Professionelles Design."
    )
    image_url = img_gen.generate_and_upload(image_prompt, size="1:1")
    print(f"[{args.account}] Bild hochgeladen: {image_url}")

    # Caption generieren
    caption = cap_writer.write_caption(topic, "feed", pillar, affiliate_cta)
    print(f"[{args.account}] Caption:\n{caption[:200]}...")

    if args.dry_run:
        print(f"[{args.account}] Dry-Run — kein echter Post.")
        return

    # Posten
    publisher = InstagramPublisher(cfg["ig_access_token"], cfg["ig_account_id"])
    media_id = publisher.post_feed_image(image_url, caption)
    print(f"[{args.account}] Gepostet: media_id={media_id}")

    state.mark_queue_item_done(item["id"], media_id)
    state.mark_topic_used(topic)


if __name__ == "__main__":
    main()
