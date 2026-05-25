import time
import requests


GRAPH_BASE = "https://graph.facebook.com/v21.0"


class InstagramPublisher:
    def __init__(self, access_token: str, account_id: str):
        self.token = access_token
        self.account_id = account_id

    def _get(self, path: str, params: dict = None) -> dict:
        params = params or {}
        params["access_token"] = self.token
        r = requests.get(f"{GRAPH_BASE}/{path}", params=params, timeout=30)
        r.raise_for_status()
        return r.json()

    def _post(self, path: str, data: dict) -> dict:
        data["access_token"] = self.token
        r = requests.post(f"{GRAPH_BASE}/{path}", data=data, timeout=60)
        r.raise_for_status()
        return r.json()

    # ------------------------------------------------------------------
    # Feed post (image)
    # ------------------------------------------------------------------

    def post_feed_image(self, image_url: str, caption: str) -> str:
        container = self._post(
            f"{self.account_id}/media",
            {"image_url": image_url, "caption": caption},
        )
        container_id = container["id"]
        self._wait_for_container(container_id)
        result = self._post(
            f"{self.account_id}/media_publish",
            {"creation_id": container_id},
        )
        return result["id"]

    # ------------------------------------------------------------------
    # Story (image)
    # ------------------------------------------------------------------

    def post_story_image(self, image_url: str) -> str:
        container = self._post(
            f"{self.account_id}/media",
            {"image_url": image_url, "media_type": "IMAGE", "is_story": True},
        )
        container_id = container["id"]
        self._wait_for_container(container_id)
        result = self._post(
            f"{self.account_id}/media_publish",
            {"creation_id": container_id},
        )
        return result["id"]

    # ------------------------------------------------------------------
    # Reel (video)
    # ------------------------------------------------------------------

    def post_reel(self, video_url: str, caption: str, cover_url: str = None) -> str:
        data = {
            "media_type": "REELS",
            "video_url": video_url,
            "caption": caption,
            "share_to_feed": True,
        }
        if cover_url:
            data["cover_url"] = cover_url
        container = self._post(f"{self.account_id}/media", data)
        container_id = container["id"]
        self._wait_for_container(container_id, max_wait=120)
        result = self._post(
            f"{self.account_id}/media_publish",
            {"creation_id": container_id},
        )
        return result["id"]

    # ------------------------------------------------------------------
    # Comments
    # ------------------------------------------------------------------

    def get_recent_comments(self, media_id: str) -> list[dict]:
        data = self._get(
            f"{media_id}/comments",
            {"fields": "id,username,text,timestamp"},
        )
        return data.get("data", [])

    def reply_to_comment(self, media_id: str, message: str) -> str:
        result = self._post(
            f"{media_id}/replies",
            {"message": message},
        )
        return result["id"]

    def get_recent_media(self, limit: int = 10) -> list[dict]:
        data = self._get(
            f"{self.account_id}/media",
            {"fields": "id,caption,timestamp,media_type", "limit": limit},
        )
        return data.get("data", [])

    # ------------------------------------------------------------------
    # Token refresh
    # ------------------------------------------------------------------

    def refresh_long_lived_token(self) -> str:
        r = requests.get(
            f"{GRAPH_BASE}/oauth/access_token",
            params={
                "grant_type": "fb_exchange_token",
                "client_id": "",  # filled from env if needed
                "client_secret": "",
                "fb_exchange_token": self.token,
                "access_token": self.token,
            },
            timeout=30,
        )
        r.raise_for_status()
        return r.json()["access_token"]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _wait_for_container(self, container_id: str, max_wait: int = 60):
        for _ in range(max_wait // 5):
            status = self._get(container_id, {"fields": "status_code,status"})
            code = status.get("status_code", "")
            if code == "FINISHED":
                return
            if code == "ERROR":
                raise RuntimeError(f"Media container fehlgeschlagen: {status}")
            time.sleep(5)
        raise TimeoutError(f"Container {container_id} wurde nicht fertig innerhalb {max_wait}s")
