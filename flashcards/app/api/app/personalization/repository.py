import json
import logging

from ..repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class UserPrefsRepository(BaseRepository):
    def ensure_defaults(self, user_id: str) -> None:
        self._conn.execute(
            """
            INSERT OR IGNORE INTO user_prefs(user_id, local_only, cloud_sync_enabled, encrypt_at_rest, prefs_json, created_at, updated_at)
            VALUES(?, 1, 0, 0, '{}', strftime('%Y-%m-%dT%H:%M:%fZ','now'), strftime('%Y-%m-%dT%H:%M:%fZ','now'));
            """,
            (user_id,),
        )

    def get_prefs(self, user_id: str) -> dict:
        self.ensure_defaults(user_id)
        row = self._conn.execute(
            "SELECT user_id, local_only, cloud_sync_enabled, encrypt_at_rest, prefs_json, created_at, updated_at FROM user_prefs WHERE user_id = ?;",
            (user_id,),
        ).fetchone()
        if not row:
            return {"user_id": user_id, "local_only": 1, "cloud_sync_enabled": 0, "encrypt_at_rest": 0, "prefs": {}}
        d = dict(row)
        try:
            d["prefs"] = json.loads(d.pop("prefs_json") or "{}")
        except Exception:
            logger.debug("Invalid user_prefs prefs_json (parse error)", extra={"user_id": user_id})
            d["prefs"] = {}
        return d

    def update_prefs(self, user_id: str, *, local_only: int | None = None, cloud_sync_enabled: int | None = None, prefs: dict | None = None) -> None:
        self.ensure_defaults(user_id)
        current = self.get_prefs(user_id)
        new_local = int(current["local_only"]) if local_only is None else int(local_only)
        new_cloud = int(current["cloud_sync_enabled"]) if cloud_sync_enabled is None else int(cloud_sync_enabled)
        merged = dict(current.get("prefs") or {})
        if prefs:
            merged.update(prefs)
        self._conn.execute(
            """
            UPDATE user_prefs
            SET local_only = ?, cloud_sync_enabled = ?, prefs_json = ?, updated_at = strftime('%Y-%m-%dT%H:%M:%fZ','now')
            WHERE user_id = ?;
            """,
            (new_local, new_cloud, json.dumps(merged, ensure_ascii=False, separators=(",", ":")), user_id),
        )


class BanditRepository(BaseRepository):
    def ensure_arms(self, *, user_id: str, experiment_key: str, arm_keys: list[str]) -> None:
        for arm in arm_keys:
            self._conn.execute(
                """
                INSERT OR IGNORE INTO bandit_state(user_id, experiment_key, arm_key, pulls, reward_sum, created_at, updated_at)
                VALUES(?, ?, ?, 0, 0, strftime('%Y-%m-%dT%H:%M:%fZ','now'), strftime('%Y-%m-%dT%H:%M:%fZ','now'));
                """,
                (user_id, experiment_key, arm),
            )

    def list_arms(self, *, user_id: str, experiment_key: str) -> list[dict]:
        rows = self._conn.execute(
            """
            SELECT arm_key, pulls, reward_sum
            FROM bandit_state
            WHERE user_id = ? AND experiment_key = ?
            ORDER BY arm_key ASC;
            """,
            (user_id, experiment_key),
        ).fetchall()
        return [dict(r) for r in rows]

    def update_arm(self, *, user_id: str, experiment_key: str, arm_key: str, reward: float) -> None:
        self._conn.execute(
            """
            UPDATE bandit_state
            SET pulls = pulls + 1,
                reward_sum = reward_sum + ?,
                updated_at = strftime('%Y-%m-%dT%H:%M:%fZ','now')
            WHERE user_id = ? AND experiment_key = ? AND arm_key = ?;
            """,
            (float(reward), user_id, experiment_key, arm_key),
        )


class FsrsParamsRepository(BaseRepository):
    def ensure_defaults(self, user_id: str) -> None:
        self._conn.execute(
            """
            INSERT OR IGNORE INTO user_fsrs_params(user_id, stability_multiplier, updated_at)
            VALUES(?, 1.0, strftime('%Y-%m-%dT%H:%M:%fZ','now'));
            """,
            (user_id,),
        )

    def get_params(self, user_id: str) -> dict:
        self.ensure_defaults(user_id)
        row = self._conn.execute(
            "SELECT user_id, stability_multiplier, updated_at FROM user_fsrs_params WHERE user_id = ?;",
            (user_id,),
        ).fetchone()
        return dict(row) if row else {"user_id": user_id, "stability_multiplier": 1.0}

    def set_stability_multiplier(self, user_id: str, mult: float) -> None:
        self.ensure_defaults(user_id)
        self._conn.execute(
            """
            UPDATE user_fsrs_params
            SET stability_multiplier = ?, updated_at = strftime('%Y-%m-%dT%H:%M:%fZ','now')
            WHERE user_id = ?;
            """,
            (float(mult), user_id),
        )

