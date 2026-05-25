import base64
import io
import time
import requests
from pathlib import Path


class ImageGenerator:
    def __init__(self, config: dict):
        self.config = config
        self.prefer_free = config.get("prefer_free_images", False)
        self.openai_key = config.get("openai_api_key", "")
        self.hf_token = config.get("hf_token", "")
        self.imgbb_key = config.get("imgbb_api_key", "")
        self.niche_style = config.get("pillars", {}).get("image_style", "")

    def generate_and_upload(self, prompt: str, size: str = "1:1") -> str:
        full_prompt = self._build_prompt(prompt, size)
        image_bytes = self._generate(full_prompt, size)
        return self._upload_imgbb(image_bytes)

    def _build_prompt(self, prompt: str, size: str) -> str:
        base_style = self.niche_style or (
            "Clean minimalist infographic, modern flat design, professional color scheme, "
            "no clutter, data visualization style, German text labels"
        )
        aspect = "vertical 9:16 format" if size == "9:16" else "square format"
        return f"{base_style}, {aspect}. {prompt}"

    def _generate(self, prompt: str, size: str) -> bytes:
        if self.prefer_free or not self.openai_key:
            return self._hf_generate(prompt, size)
        try:
            return self._dalle_generate(prompt, size)
        except Exception as e:
            print(f"DALL-E fehlgeschlagen ({e}), Fallback auf HuggingFace")
            return self._hf_generate(prompt, size)

    def _dalle_generate(self, prompt: str, size: str) -> bytes:
        dalle_size = "1024x1792" if size == "9:16" else "1024x1024"
        headers = {
            "Authorization": f"Bearer {self.openai_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "dall-e-3",
            "prompt": prompt[:4000],
            "n": 1,
            "size": dalle_size,
            "quality": "standard",
            "response_format": "b64_json",
        }
        r = requests.post(
            "https://api.openai.com/v1/images/generations",
            json=payload,
            headers=headers,
            timeout=60,
        )
        r.raise_for_status()
        return base64.b64decode(r.json()["data"][0]["b64_json"])

    def _hf_generate(self, prompt: str, size: str) -> bytes:
        # SDXL-Turbo via HuggingFace Inference API (kostenlos mit Rate Limit)
        headers = {}
        if self.hf_token:
            headers["Authorization"] = f"Bearer {self.hf_token}"
        payload = {"inputs": prompt[:500]}
        for attempt in range(3):
            r = requests.post(
                "https://api-inference.huggingface.co/models/stabilityai/sdxl-turbo",
                json=payload,
                headers=headers,
                timeout=60,
            )
            if r.status_code == 503:
                wait = int(r.json().get("estimated_time", 20))
                print(f"HuggingFace Modell lädt, warte {wait}s...")
                time.sleep(min(wait, 30))
                continue
            r.raise_for_status()
            return r.content
        raise RuntimeError("HuggingFace nach 3 Versuchen nicht erreichbar")

    def _upload_imgbb(self, image_bytes: bytes) -> str:
        encoded = base64.b64encode(image_bytes).decode("utf-8")
        r = requests.post(
            "https://api.imgbb.com/1/upload",
            data={"key": self.imgbb_key, "image": encoded},
            timeout=30,
        )
        r.raise_for_status()
        return r.json()["data"]["url"]
