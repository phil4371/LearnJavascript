import json
import anthropic
import requests
from datetime import date, timedelta


WEEKLY_SCHEDULE = [
    # (wochentag_offset, post_type)  — 0=Mo, 1=Di, ...
    (0, "story"),
    (0, "feed"),
    (1, "story"),
    (1, "reel"),
    (1, "feed"),
    (2, "story"),
    (2, "feed"),
    (3, "story"),
    (3, "feed"),
    (4, "story"),
    (4, "reel"),
    (4, "feed"),
    (5, "feed"),
    (6, "story"),
    (6, "feed"),
]


class ContentPlanner:
    def __init__(self, config: dict):
        self.config = config
        self.pillars = config.get("pillars", {})
        self.knowledge = config.get("knowledge", "")
        self.use_ollama = config.get("use_ollama", False)

    def generate_weekly_plan(self, used_topics: list[str]) -> list[dict]:
        monday = self._next_monday()
        prompt = self._build_prompt(used_topics, monday)
        raw = self._generate(prompt)
        plan = self._parse_plan(raw, monday)
        return plan

    def _next_monday(self) -> date:
        today = date.today()
        days_ahead = 7 - today.weekday()
        return today + timedelta(days=days_ahead)

    def _build_prompt(self, used_topics: list[str], monday: date) -> str:
        pillars_list = "\n".join(
            f"- {p['name']}: {p['description']}"
            for p in self.pillars.get("content_pillars", [])
        )
        used_str = ", ".join(used_topics[-20:]) if used_topics else "keine"
        niche = self.pillars.get("niche_name", "")
        tone = self.pillars.get("tone", "")

        # Affiliate-Säulen hervorheben
        affiliate_pillars = [
            p["name"]
            for p in self.pillars.get("content_pillars", [])
            if p.get("has_affiliate")
        ]

        return (
            f"Erstelle einen Instagram-Wochenplan für die Nische: {niche}\n"
            f"Tonalität: {tone}\n\n"
            f"Content-Säulen:\n{pillars_list}\n\n"
            f"Wissen/Kontext:\n{self.knowledge[:2000]}\n\n"
            f"BEREITS VERWENDETE THEMEN (bitte vermeiden): {used_str}\n\n"
            f"Säulen mit Affiliate-Potenzial: {', '.join(affiliate_pillars)}\n"
            f"Mindestens 3 Posts dieser Woche sollten Affiliate-CTAs haben.\n\n"
            f"Erstelle einen Plan für folgende 15 Posts (Woche ab {monday.isoformat()}):\n"
            + "\n".join(
                f"{i+1}. {monday + timedelta(days=d)} — {pt}"
                for i, (d, pt) in enumerate(WEEKLY_SCHEDULE)
            )
            + "\n\nAntworte NUR mit gültigem JSON-Array. Jedes Element hat:\n"
            '{"date": "YYYY-MM-DD", "post_type": "feed|story|reel", '
            '"topic": "konkretes Thema auf Deutsch", "pillar": "Säulenname", '
            '"affiliate_cta": true|false}\n'
            "Keine Erklärung, kein Markdown, nur das JSON-Array."
        )

    def _generate(self, prompt: str) -> str:
        if self.use_ollama:
            return self._ollama(prompt)
        return self._claude(prompt)

    def _claude(self, prompt: str) -> str:
        client = anthropic.Anthropic(api_key=self.config["anthropic_api_key"])
        msg = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text.strip()

    def _ollama(self, prompt: str) -> str:
        base_url = self.config.get("ollama_base_url", "http://localhost:11434")
        model = self.config.get("ollama_model", "qwen2.5:3b")
        r = requests.post(
            f"{base_url}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=180,
        )
        r.raise_for_status()
        return r.json()["response"].strip()

    def _parse_plan(self, raw: str, monday: date) -> list[dict]:
        # JSON-Block aus der Antwort extrahieren
        start = raw.find("[")
        end = raw.rfind("]") + 1
        if start == -1 or end == 0:
            raise ValueError(f"Kein JSON-Array in der Planer-Antwort gefunden:\n{raw[:500]}")
        plan = json.loads(raw[start:end])

        # Fehlende Felder auffüllen
        for item in plan:
            item.setdefault("pillar", "")
            item.setdefault("affiliate_cta", False)

        return plan
