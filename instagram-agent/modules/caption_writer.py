import anthropic
import requests


class CaptionWriter:
    def __init__(self, config: dict):
        self.config = config
        self.pillars = config.get("pillars", {})
        self.use_ollama = config.get("use_ollama", False)

    def write_caption(self, topic: str, post_type: str, pillar: str, affiliate_cta: bool = False) -> str:
        affiliate_info = self._get_affiliate_info(pillar) if affiliate_cta else ""
        prompt = self._build_prompt(topic, post_type, pillar, affiliate_info)
        return self._generate(prompt)

    def write_story_text(self, topic: str, story_type: str = "tip") -> str:
        prompt = (
            f"Erstelle kurzen Story-Text auf Deutsch für Instagram zum Thema: {topic}\n"
            f"Story-Typ: {story_type} (z.B. 'poll', 'tip', 'quote', 'quiz')\n"
            f"Nische: {self.pillars.get('niche_name', '')}\n"
            f"Stil: {self.pillars.get('tone', 'freundlich, informativ')}\n"
            f"Max. 3 kurze Zeilen. Kein Hashtag.\n"
        )
        return self._generate(prompt)

    def _build_prompt(self, topic: str, post_type: str, pillar: str, affiliate_info: str) -> str:
        niche = self.pillars.get("niche_name", "")
        tone = self.pillars.get("tone", "freundlich, informativ, auf Augenhöhe")
        hashtags = ", ".join(self.pillars.get("hashtags", [])[:28])
        disclaimer = self.pillars.get("disclaimer", "")

        affiliate_block = ""
        if affiliate_info:
            affiliate_block = (
                f"\nAffiliate-CTA: Füge am Ende einen natürlichen Call-to-Action ein: "
                f"'{affiliate_info}'. Keine direkte URL in der Caption — immer 'Link in Bio'.\n"
                f"Kennzeichne mit *Werbung oder *Affiliate am Anfang oder Ende.\n"
            )

        return (
            f"Schreibe eine Instagram-Caption auf Deutsch.\n\n"
            f"Thema: {topic}\n"
            f"Post-Typ: {post_type}\n"
            f"Content-Säule: {pillar}\n"
            f"Nische: {niche}\n"
            f"Tonalität: {tone}\n"
            f"{affiliate_block}"
            f"Länge: 100–200 Wörter. Mit 1–2 Emojis. Persönlich, kein Marketingsprech.\n"
            f"Am Ende: 20–25 Hashtags aus dieser Liste verwenden: {hashtags}\n"
            f"{'Disclaimer: ' + disclaimer if disclaimer else ''}\n"
            f"Gib NUR die fertige Caption aus, ohne Erklärung."
        )

    def _get_affiliate_info(self, pillar: str) -> str:
        ctas = self.pillars.get("affiliate_ctas", {})
        return ctas.get(pillar, ctas.get("default", ""))

    def _generate(self, prompt: str) -> str:
        if self.use_ollama:
            return self._ollama_generate(prompt)
        return self._claude_generate(prompt)

    def _claude_generate(self, prompt: str) -> str:
        client = anthropic.Anthropic(api_key=self.config["anthropic_api_key"])
        msg = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=600,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text.strip()

    def _ollama_generate(self, prompt: str) -> str:
        base_url = self.config.get("ollama_base_url", "http://localhost:11434")
        model = self.config.get("ollama_model", "qwen2.5:3b")
        r = requests.post(
            f"{base_url}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=120,
        )
        r.raise_for_status()
        return r.json()["response"].strip()
