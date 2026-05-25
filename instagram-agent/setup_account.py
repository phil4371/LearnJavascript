#!/usr/bin/env python3
"""
Einmaliges Setup für einen Account:
  1. DB initialisieren
  2. API-Verbindungen prüfen
  3. Ersten Wochenplan generieren und in DB speichern
"""
import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import load_account_config
from modules.state_manager import StateManager
from modules.content_planner import ContentPlanner
from modules.instagram_publisher import InstagramPublisher
from modules.image_generator import ImageGenerator


def check_apis(cfg: dict):
    print("\n--- API-Verbindungen prüfen ---")
    errors = []

    # Anthropic
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=cfg["anthropic_api_key"])
        client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=5,
            messages=[{"role": "user", "content": "Hi"}],
        )
        print("  ✓ Anthropic (Claude Haiku)")
    except Exception as e:
        print(f"  ✗ Anthropic: {e}")
        errors.append("Anthropic")

    # OpenAI
    if cfg.get("openai_api_key") and not cfg.get("prefer_free_images"):
        try:
            import openai
            c = openai.OpenAI(api_key=cfg["openai_api_key"])
            c.models.list()
            print("  ✓ OpenAI (DALL-E 3)")
        except Exception as e:
            print(f"  ✗ OpenAI: {e}")
            errors.append("OpenAI")
    else:
        print("  ~ OpenAI übersprungen (PREFER_FREE_IMAGES=true oder kein Key)")

    # Instagram
    try:
        pub = InstagramPublisher(cfg["ig_access_token"], cfg["ig_account_id"])
        pub.get_recent_media(limit=1)
        print("  ✓ Instagram Graph API")
    except Exception as e:
        print(f"  ✗ Instagram: {e}")
        errors.append("Instagram")

    # imgbb
    try:
        import requests
        r = requests.get(
            "https://api.imgbb.com/1/upload",
            params={"key": cfg["imgbb_api_key"]},
            timeout=10,
        )
        if r.status_code in (400, 200):
            print("  ✓ imgbb (Bild-Hosting)")
        else:
            raise Exception(f"HTTP {r.status_code}")
    except Exception as e:
        print(f"  ✗ imgbb: {e}")
        errors.append("imgbb")

    return errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--account", required=True)
    parser.add_argument("--skip-api-check", action="store_true")
    parser.add_argument("--skip-plan", action="store_true")
    args = parser.parse_args()

    print(f"\n=== Setup: {args.account} ===")

    cfg = load_account_config(args.account)

    # DB initialisieren
    state = StateManager(cfg["account_dir"])
    print(f"✓ Datenbank initialisiert: {cfg['account_dir']}/data/agent_state.db")

    if not args.skip_api_check:
        errors = check_apis(cfg)
        if errors:
            print(f"\n⚠️  Fehler bei: {', '.join(errors)}")
            print("Prüfe die .env-Datei und versuche erneut.")
            sys.exit(1)

    if not args.skip_plan:
        print("\n--- Ersten Wochenplan generieren ---")
        planner = ContentPlanner(cfg)
        plan = planner.generate_weekly_plan(used_topics=[])
        state.queue_weekly_plan(plan)
        print(f"✓ {len(plan)} Posts in DB gespeichert:")
        for item in plan:
            cta = " [Affiliate]" if item.get("affiliate_cta") else ""
            print(f"  {item['date']} {item['post_type']:5s} | {item['topic'][:50]}{cta}")

    print(f"\n✅ Setup abgeschlossen für: {args.account}")
    print(f"\nNächster Schritt:")
    print(f"  Dry-Run testen:    python runners/run_daily_feed.py --account {args.account} --dry-run")
    print(f"  Ersten Post:       python runners/run_daily_feed.py --account {args.account}")


if __name__ == "__main__":
    main()
