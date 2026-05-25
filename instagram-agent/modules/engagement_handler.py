import anthropic
import requests


class EngagementHandler:
    def __init__(self, config: dict):
        self.config = config
        self.pillars = config.get("pillars", {})
        self.use_ollama = config.get("use_ollama", False)

    def generate_reply(self, comment_text: str, username: str, post_topic: str) -> str:
        prompt = self._build_prompt(comment_text, username, post_topic)
        return self._generate(prompt)

    def _build_prompt(self, comment: str, username: str, topic: str) -> str:
        niche = self.pillars.get("niche_name", "")
        tone = self.pillars.get("tone", "freundlich, hilfreich")
        account_persona = self.pillars.get("account_persona", "freundlicher Experte")
        return (
            f"Du bist der Instagram-Account-Manager für einen deutschen {niche}-Account.\n"
            f"Persona: {account_persona}\n"
            f"Tonalität: {tone}\n\n"
            f"Antworte auf diesen Kommentar von @{username}:\n"
            f"Kommentar: \"{comment}\"\n"
            f"Post-Thema war: {topic}\n\n"
            f"Schreibe eine kurze, freundliche Antwort auf Deutsch (1–3 Sätze).\n"
            f"Verwende gelegentlich den @{username}-Hinweis.\n"
            f"Keine Hashtags. Kein Spam. Keine Werbung.\n"
            f"Gib NUR die Antwort aus, ohne Erklärung."
        )

    def _generate(self, prompt: str) -> str:
        if self.use_ollama:
            return self._ollama(prompt)
        return self._claude(prompt)

    def _claude(self, prompt: str) -> str:
        client = anthropic.Anthropic(api_key=self.config["anthropic_api_key"])
        msg = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=150,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text.strip()

    def _ollama(self, prompt: str) -> str:
        base_url = self.config.get("ollama_base_url", "http://localhost:11434")
        model = self.config.get("ollama_model", "qwen2.5:3b")
        r = requests.post(
            f"{base_url}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=60,
        )
        r.raise_for_status()
        return r.json()["response"].strip()
