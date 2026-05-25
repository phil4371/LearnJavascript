import os
import json
import argparse
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent


def load_account_config(account_name: str) -> dict:
    account_dir = BASE_DIR / "accounts" / account_name
    if not account_dir.exists():
        raise ValueError(f"Account-Verzeichnis nicht gefunden: {account_dir}")

    # Account-spezifische .env laden
    load_dotenv(account_dir / ".env")
    # Geteilte .env (gemeinsame API-Keys) laden ohne Überschreiben
    shared_env = BASE_DIR / ".env.shared"
    if shared_env.exists():
        load_dotenv(shared_env, override=False)

    pillars_file = account_dir / "pillars.json"
    knowledge_file = account_dir / "knowledge.md"

    config = {
        "account_name": account_name,
        "account_dir": account_dir,
        # Instagram / Meta
        "ig_access_token": os.getenv("IG_ACCESS_TOKEN"),
        "ig_account_id": os.getenv("IG_ACCOUNT_ID"),
        # Shared API-Keys (aus .env.shared oder account .env)
        "anthropic_api_key": os.getenv("ANTHROPIC_API_KEY"),
        "openai_api_key": os.getenv("OPENAI_API_KEY"),
        "hf_token": os.getenv("HF_TOKEN", ""),
        "imgbb_api_key": os.getenv("IMGBB_API_KEY"),
        # Feature-Flags
        "prefer_free_images": os.getenv("PREFER_FREE_IMAGES", "false").lower() == "true",
        "use_ollama": os.getenv("USE_OLLAMA", "false").lower() == "true",
        "ollama_model": os.getenv("OLLAMA_MODEL", "qwen2.5:3b"),
        "ollama_base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
    }

    config["pillars"] = json.loads(pillars_file.read_text()) if pillars_file.exists() else {}
    config["knowledge"] = knowledge_file.read_text() if knowledge_file.exists() else ""

    return config


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--account", required=True, help="Account-Name (Unterverzeichnis in accounts/)")
    parser.add_argument("--dry-run", action="store_true", help="Nur generieren, nicht posten")
    return parser.parse_known_args()[0]
