#!/usr/bin/env python3
"""Generiert den Wochenplan für die nächste Woche und speichert ihn in der DB."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import load_account_config, parse_args
from modules.state_manager import StateManager
from modules.content_planner import ContentPlanner


def main():
    args = parse_args()
    cfg = load_account_config(args.account)

    state = StateManager(cfg["account_dir"])
    planner = ContentPlanner(cfg)

    used_topics = state.get_used_topics(days=14)
    print(f"[{args.account}] {len(used_topics)} Themen in den letzten 14 Tagen verwendet")

    plan = planner.generate_weekly_plan(used_topics)
    print(f"[{args.account}] {len(plan)} Posts geplant für die nächste Woche:")
    for item in plan:
        cta = " [Affiliate]" if item.get("affiliate_cta") else ""
        print(f"  {item['date']} {item['post_type']:5s} | {item['pillar']:20s} | {item['topic']}{cta}")

    if args.dry_run:
        print(f"[{args.account}] Dry-Run — Plan nicht gespeichert.")
        return

    state.queue_weekly_plan(plan)
    print(f"[{args.account}] Plan gespeichert.")


if __name__ == "__main__":
    main()
