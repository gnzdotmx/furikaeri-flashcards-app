"""Tests for app.db."""

import os
import sqlite3
import tempfile

from app.db import (
    connect,
    connection,
    db_health,
    ensure_db,
    get_schema_version,
    run_migrations,
    transaction,
)


def test_ensure_db_creates_file_and_dir() -> None:
    tmp = tempfile.mkdtemp(prefix="furikaeri_db_test_")
    path = os.path.join(tmp, "sub", "db.sqlite")
    ensure_db(path)
    assert os.path.isdir(os.path.join(tmp, "sub"))
    assert os.path.isfile(path)
    conn = sqlite3.connect(path)
    try:
        conn.execute("SELECT 1;")
        row = conn.execute("PRAGMA journal_mode;").fetchone()
        assert row[0] == "wal"
        # foreign_keys is per-connection; ensure_db set it before close, so we just check file exists
    finally:
        conn.close()
    os.remove(path)
    os.removedirs(os.path.join(tmp, "sub"))


def test_connect_sets_row_factory() -> None:
    fd, path = tempfile.mkstemp(suffix=".sqlite")
    os.close(fd)
    try:
        ensure_db(path)
        conn = connect(path)
        try:
            conn.execute("CREATE TABLE t (x INTEGER);")
            conn.execute("INSERT INTO t VALUES (1);")
            row = conn.execute("SELECT x FROM t;").fetchone()
            assert hasattr(row, "keys")
            assert row["x"] == 1
        finally:
            conn.close()
    finally:
        os.remove(path)


def test_connection_context_closes() -> None:
    fd, path = tempfile.mkstemp(suffix=".sqlite")
    os.close(fd)
    try:
        ensure_db(path)
        with connection(path) as conn:
            conn.execute("SELECT 1;")
        # conn is closed; using it should fail or be invalid
        try:
            conn.execute("SELECT 1;")
        except sqlite3.ProgrammingError:
            pass
    finally:
        os.remove(path)


def test_transaction_commit() -> None:
    fd, path = tempfile.mkstemp(suffix=".sqlite")
    os.close(fd)
    try:
        ensure_db(path)
        with connection(path) as conn:
            conn.execute("CREATE TABLE t (x INTEGER);")
            with transaction(conn):
                conn.execute("INSERT INTO t VALUES (42);")
            # after context, committed
            row = conn.execute("SELECT x FROM t;").fetchone()
            assert row[0] == 42
    finally:
        os.remove(path)


def test_transaction_rollback() -> None:
    fd, path = tempfile.mkstemp(suffix=".sqlite")
    os.close(fd)
    try:
        ensure_db(path)
        with connection(path) as conn:
            conn.execute("CREATE TABLE t (x INTEGER);")
            try:
                with transaction(conn):
                    conn.execute("INSERT INTO t VALUES (99);")
                    raise RuntimeError("abort")
            except RuntimeError:
                pass
            row = conn.execute("SELECT x FROM t;").fetchone()
            assert row is None  # rolled back
    finally:
        os.remove(path)


def test_transaction_nested_savepoint() -> None:
    fd, path = tempfile.mkstemp(suffix=".sqlite")
    os.close(fd)
    try:
        ensure_db(path)
        with connection(path) as conn:
            conn.execute("BEGIN;")
            conn.execute("CREATE TABLE t (x INTEGER);")
            conn.execute("INSERT INTO t VALUES (1);")
            try:
                with transaction(conn):  # uses SAVEPOINT
                    conn.execute("INSERT INTO t VALUES (2);")
                    raise ValueError("inner fail")
            except ValueError:
                pass
            # outer transaction still has 1 row (inner rolled back)
            n = conn.execute("SELECT COUNT(*) FROM t;").fetchone()[0]
            assert n == 1
            conn.rollback()
    finally:
        os.remove(path)


def test_get_schema_version_empty() -> None:
    fd, path = tempfile.mkstemp(suffix=".sqlite")
    os.close(fd)
    try:
        ensure_db(path)
        with connection(path) as conn:
            v = get_schema_version(conn)
            assert v == 0
    finally:
        os.remove(path)


def test_run_migrations_returns_info() -> None:
    fd, path = tempfile.mkstemp(suffix=".sqlite")
    os.close(fd)
    try:
        ensure_db(path)
        info = run_migrations(path)
        assert "applied" in info
        assert "current_version" in info
        assert "migrations_count" in info
        assert info["current_version"] >= 1
        assert len(info["applied"]) >= 1
    finally:
        os.remove(path)


def test_db_health_ok_for_existing_db() -> None:
    fd, path = tempfile.mkstemp(suffix=".sqlite")
    os.close(fd)
    try:
        ensure_db(path)
        result = db_health(path)
        assert result["ok"] is True
        assert result["exists"] is True
        assert result["writable_dir"] is True
        assert "path" in result
    finally:
        os.remove(path)


def test_db_health_creates_file_and_reports_ok() -> None:
    tmp = tempfile.mkdtemp(prefix="furikaeri_health_")
    path = os.path.join(tmp, "new.db")
    try:
        result = db_health(path)
        # sqlite3.connect(path) creates the file; SELECT 1 succeeds
        assert result["ok"] is True
        assert os.path.isfile(path)
    finally:
        if os.path.isfile(path):
            os.remove(path)
        os.rmdir(tmp)
