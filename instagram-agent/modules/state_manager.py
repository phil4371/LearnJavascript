import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from contextlib import contextmanager


class StateManager:
    def __init__(self, account_dir: Path):
        self.db_path = account_dir / "data" / "agent_state.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_db(self):
        with self._conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS posts (
                    id INTEGER PRIMARY KEY,
                    post_type TEXT NOT NULL,
                    topic TEXT NOT NULL,
                    pillar TEXT,
                    ig_media_id TEXT,
                    caption TEXT,
                    image_url TEXT,
                    posted_at TEXT,
                    status TEXT DEFAULT 'pending'
                );
                CREATE TABLE IF NOT EXISTS content_queue (
                    id INTEGER PRIMARY KEY,
                    scheduled_date TEXT NOT NULL,
                    post_type TEXT NOT NULL,
                    topic TEXT NOT NULL,
                    pillar TEXT,
                    affiliate_cta INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'pending',
                    created_at TEXT DEFAULT (datetime('now'))
                );
                CREATE TABLE IF NOT EXISTS comments (
                    id INTEGER PRIMARY KEY,
                    ig_comment_id TEXT UNIQUE NOT NULL,
                    ig_media_id TEXT NOT NULL,
                    username TEXT,
                    text TEXT,
                    replied INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT (datetime('now'))
                );
                CREATE TABLE IF NOT EXISTS used_topics (
                    id INTEGER PRIMARY KEY,
                    topic TEXT NOT NULL,
                    used_at TEXT DEFAULT (datetime('now'))
                );
            """)

    def get_next_queued_post(self, post_type: str) -> dict | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM content_queue WHERE post_type = ? AND status = 'pending' "
                "ORDER BY scheduled_date ASC LIMIT 1",
                (post_type,),
            ).fetchone()
            return dict(row) if row else None

    def mark_queue_item_done(self, item_id: int, ig_media_id: str = None):
        with self._conn() as conn:
            conn.execute(
                "UPDATE content_queue SET status = 'posted' WHERE id = ?", (item_id,)
            )
            if ig_media_id:
                conn.execute(
                    "INSERT INTO posts (post_type, topic, pillar, ig_media_id, posted_at, status) "
                    "SELECT post_type, topic, pillar, ?, datetime('now'), 'posted' "
                    "FROM content_queue WHERE id = ?",
                    (ig_media_id, item_id),
                )

    def get_used_topics(self, days: int = 14) -> list[str]:
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT topic FROM used_topics WHERE used_at > ?", (cutoff,)
            ).fetchall()
            return [r["topic"] for r in rows]

    def mark_topic_used(self, topic: str):
        with self._conn() as conn:
            conn.execute("INSERT INTO used_topics (topic) VALUES (?)", (topic,))

    def queue_weekly_plan(self, plan: list[dict]):
        with self._conn() as conn:
            conn.execute("DELETE FROM content_queue WHERE status = 'pending'")
            conn.executemany(
                "INSERT INTO content_queue (scheduled_date, post_type, topic, pillar, affiliate_cta) "
                "VALUES (:date, :post_type, :topic, :pillar, :affiliate_cta)",
                [
                    {
                        "date": item["date"],
                        "post_type": item["post_type"],
                        "topic": item["topic"],
                        "pillar": item.get("pillar", ""),
                        "affiliate_cta": int(item.get("affiliate_cta", False)),
                    }
                    for item in plan
                ],
            )

    def save_comment(self, ig_comment_id: str, ig_media_id: str, username: str, text: str):
        with self._conn() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO comments (ig_comment_id, ig_media_id, username, text) "
                "VALUES (?, ?, ?, ?)",
                (ig_comment_id, ig_media_id, username, text),
            )

    def get_unanswered_comments(self, limit: int = 20) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM comments WHERE replied = 0 ORDER BY created_at ASC LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]

    def mark_comment_replied(self, ig_comment_id: str):
        with self._conn() as conn:
            conn.execute(
                "UPDATE comments SET replied = 1 WHERE ig_comment_id = ?", (ig_comment_id,)
            )

    def get_recent_posts(self, limit: int = 5) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM posts ORDER BY posted_at DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(r) for r in rows]

    def get_recent_ig_media_ids(self, limit: int = 10) -> list[str]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT ig_media_id FROM posts WHERE ig_media_id IS NOT NULL "
                "ORDER BY posted_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [r["ig_media_id"] for r in rows]
