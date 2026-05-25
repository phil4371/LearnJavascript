#!/usr/bin/env python3
"""Postet die nächste geplante Story für den angegebenen Account."""
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
    item = state.get_next_queued_post("story")
    if not item:
        print(f"[{args.account}] Keine Story in der Queue.")
        return

    topic = item["topic"]
    print(f"[{args.account}] Story: {topic}")

    img_gen = ImageGenerator(cfg)
    cap_writer = CaptionWriter(cfg)

    story_text = cap_writer.write_story_text(topic)

    image_prompt = (
        f"Instagram Story (9:16) zum Thema: {topic}. "
        f"Minimalistisches Design, großer Text, starke Farben. "
        f"Nische: {cfg['pillars'].get('niche_name', '')}."
    )
    image_url = img_gen.generate_and_upload(image_prompt, size="9:16")
    print(f"[{args.account}] Story-Bild: {image_url}")
    print(f"[{args.account}] Story-Text: {story_text}")

    if args.dry_run:
        print(f"[{args.account}] Dry-Run — kein echter Post.")
        return

    publisher = InstagramPublisher(cfg["ig_access_token"], cfg["ig_account_id"])
    media_id = publisher.post_story_image(image_url)
    print(f"[{args.account}] Story gepostet: {media_id}")

    state.mark_queue_item_done(item["id"], media_id)
    state.mark_topic_used(topic)


if __name__ == "__main__":
    main()
