"""Tests for app.personalization.repository."""

import os
import tempfile

from app.db import ensure_db, run_migrations, connection
from app.repositories.users import UserRepository
from app.personalization.repository import (
    BanditRepository,
    FsrsParamsRepository,
    UserPrefsRepository,
)


def _temp_db() -> str:
    fd, path = tempfile.mkstemp(suffix=".sqlite")
    os.close(fd)
    return path


def test_user_prefs_ensure_defaults_and_get() -> None:
    path = _temp_db()
    try:
        ensure_db(path)
        run_migrations(path)
        with connection(path) as conn:
            user_id = UserRepository(conn).ensure_single_user()
            repo = UserPrefsRepository(conn)
            repo.ensure_defaults(user_id)
            prefs = repo.get_prefs(user_id)
            assert prefs["user_id"] == user_id
            assert prefs["local_only"] == 1
            assert prefs["cloud_sync_enabled"] == 0
            assert prefs.get("prefs") == {}
    finally:
        os.remove(path)


def test_user_prefs_update_prefs() -> None:
    path = _temp_db()
    try:
        ensure_db(path)
        run_migrations(path)
        with connection(path) as conn:
            user_id = UserRepository(conn).ensure_single_user()
            repo = UserPrefsRepository(conn)
            repo.ensure_defaults(user_id)
            repo.update_prefs(user_id, prefs={"theme": "dark"})
            prefs = repo.get_prefs(user_id)
            assert prefs["prefs"].get("theme") == "dark"
            repo.update_prefs(user_id, local_only=0)
            prefs = repo.get_prefs(user_id)
            assert prefs["local_only"] == 0
    finally:
        os.remove(path)


def test_user_prefs_get_prefs_malformed_json_returns_empty_prefs() -> None:
    path = _temp_db()
    try:
        ensure_db(path)
        run_migrations(path)
        with connection(path) as conn:
            user_id = UserRepository(conn).ensure_single_user()
            conn.execute(
                "INSERT OR REPLACE INTO user_prefs(user_id, local_only, cloud_sync_enabled, encrypt_at_rest, prefs_json, created_at, updated_at) VALUES(?, 1, 0, 0, ?, strftime('%Y-%m-%dT%H:%M:%fZ','now'), strftime('%Y-%m-%dT%H:%M:%fZ','now'));",
                (user_id, "not json"),
            )
            conn.commit()
            repo = UserPrefsRepository(conn)
            prefs = repo.get_prefs(user_id)
            assert prefs["prefs"] == {}
    finally:
        os.remove(path)


def test_bandit_ensure_arms_list_update() -> None:
    path = _temp_db()
    try:
        ensure_db(path)
        run_migrations(path)
        with connection(path) as conn:
            user_id = UserRepository(conn).ensure_single_user()
            repo = BanditRepository(conn)
            repo.ensure_arms(user_id=user_id, experiment_key="exp1", arm_keys=["a", "b"])
            arms = repo.list_arms(user_id=user_id, experiment_key="exp1")
            assert len(arms) == 2
            assert {a["arm_key"] for a in arms} == {"a", "b"}
            assert arms[0]["pulls"] == 0
            repo.update_arm(user_id=user_id, experiment_key="exp1", arm_key="a", reward=1.0)
            arms = repo.list_arms(user_id=user_id, experiment_key="exp1")
            a_row = next(x for x in arms if x["arm_key"] == "a")
            assert a_row["pulls"] == 1
            assert float(a_row["reward_sum"]) == 1.0
    finally:
        os.remove(path)


def test_fsrs_params_ensure_get_set() -> None:
    path = _temp_db()
    try:
        ensure_db(path)
        run_migrations(path)
        with connection(path) as conn:
            user_id = UserRepository(conn).ensure_single_user()
            repo = FsrsParamsRepository(conn)
            repo.ensure_defaults(user_id)
            params = repo.get_params(user_id)
            assert params["user_id"] == user_id
            assert float(params["stability_multiplier"]) == 1.0
            repo.set_stability_multiplier(user_id, 1.2)
            params = repo.get_params(user_id)
            assert float(params["stability_multiplier"]) == 1.2
    finally:
        os.remove(path)


def test_fsrs_params_get_returns_default_stability_before_set() -> None:
    path = _temp_db()
    try:
        ensure_db(path)
        run_migrations(path)
        with connection(path) as conn:
            user_id = UserRepository(conn).ensure_single_user()
            repo = FsrsParamsRepository(conn)
            params = repo.get_params(user_id)
            assert params["stability_multiplier"] == 1.0
    finally:
        os.remove(path)
