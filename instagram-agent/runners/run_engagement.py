#!/usr/bin/env python3
"""Holt neue Kommentare und antwortet automatisch auf offene Kommentare."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import load_account_config, parse_args
from modules.state_manager import StateManager
from modules.instagram_publisher import InstagramPublisher
from modules.engagement_handler import EngagementHandler


def main():
    args = parse_args()
    cfg = load_account_config(args.account)

    state = StateManager(cfg["account_dir"])
    publisher = InstagramPublisher(cfg["ig_access_token"], cfg["ig_account_id"])
    handler = EngagementHandler(cfg)

    # Neue Kommentare von den letzten 10 Posts einsammeln
    recent_media = publisher.get_recent_media(limit=10)
    for media in recent_media:
        comments = publisher.get_recent_comments(media["id"])
        topic = media.get("caption", "")[:80]
        for c in comments:
            state.save_comment(
                ig_comment_id=c["id"],
                ig_media_id=media["id"],
                username=c.get("username", ""),
                text=c.get("text", ""),
            )

    # Auf unbeantwortete Kommentare antworten
    unanswered = state.get_unanswered_comments(limit=20)
    print(f"[{args.account}] {len(unanswered)} offene Kommentare")

    recent_posts = state.get_recent_posts(limit=5)
    post_topics = {p["ig_media_id"]: p["topic"] for p in recent_posts if p.get("ig_media_id")}

    replied = 0
    for comment in unanswered:
        topic = post_topics.get(comment["ig_media_id"], "")
        reply = handler.generate_reply(comment["text"], comment["username"], topic)

        if args.dry_run:
            print(f"  @{comment['username']}: {comment['text'][:60]}")
            print(f"  → {reply}")
            continue

        try:
            publisher.reply_to_comment(comment["ig_comment_id"], reply)
            state.mark_comment_replied(comment["ig_comment_id"])
            replied += 1
            print(f"[{args.account}] Geantwortet auf @{comment['username']}")
        except Exception as e:
            print(f"[{args.account}] Fehler bei Kommentar {comment['ig_comment_id']}: {e}")

    if not args.dry_run:
        print(f"[{args.account}] {replied} Kommentare beantwortet")


if __name__ == "__main__":
    main()
