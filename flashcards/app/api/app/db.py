import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
import uuid


def ensure_db(sqlite_path: str) -> None:
    """Create parent dir and DB file if missing; enable WAL and foreign keys."""
    p = Path(sqlite_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(p)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
    finally:
        conn.close()


def connect(sqlite_path: str) -> sqlite3.Connection:
    """Open SQLite with WAL, foreign keys, 15s busy timeout."""
    conn = sqlite3.connect(sqlite_path, timeout=15.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


@contextmanager
def connection(sqlite_path: str):
    conn = connect(sqlite_path)
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def transaction(conn: sqlite3.Connection):
    """Context manager for a transaction. Uses SAVEPOINT when already in a transaction. Savepoint name is random (no user input)."""
    if getattr(conn, "in_transaction", False):
        sp = f"sp_{uuid.uuid4().hex}"
        conn.execute(f"SAVEPOINT {sp};")
        try:
            yield
            conn.execute(f"RELEASE SAVEPOINT {sp};")
        except Exception:
            conn.execute(f"ROLLBACK TO SAVEPOINT {sp};")
            conn.execute(f"RELEASE SAVEPOINT {sp};")
            raise
        return

    conn.execute("BEGIN;")
    try:
        yield
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def _ensure_schema_migrations(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
          version INTEGER PRIMARY KEY,
          name TEXT NOT NULL,
          applied_at TEXT NOT NULL
        );
        """
    )


def get_schema_version(conn: sqlite3.Connection) -> int:
    _ensure_schema_migrations(conn)
    row = conn.execute("SELECT COALESCE(MAX(version), 0) AS v FROM schema_migrations;").fetchone()
    return int(row["v"]) if row else 0


def run_migrations(sqlite_path: str) -> dict:
    """Run app/migrations/*.sql in order. Idempotent (tracked in schema_migrations). Returns applied list, current version, count."""
    migrations_dir = Path(__file__).resolve().parent / "migrations"
    files = sorted(migrations_dir.glob("*.sql"))

    applied = []
    with connection(sqlite_path) as conn:
        _ensure_schema_migrations(conn)
        existing = {int(r["version"]) for r in conn.execute("SELECT version FROM schema_migrations;").fetchall()}

        for f in files:
            m = f.name.split("_", 1)[0]
            try:
                version = int(m)
            except ValueError:
                continue
            if version in existing:
                continue

            sql = f.read_text(encoding="utf-8")
            name = f.name
            try:
                conn.executescript(sql)
                conn.execute(
                    "INSERT INTO schema_migrations(version, name, applied_at) VALUES(?, ?, strftime('%Y-%m-%dT%H:%M:%fZ','now'));",
                    (version, name),
                )
                conn.commit()
            except Exception:
                conn.rollback()
                raise

            applied.append({"version": version, "name": name})

        current = get_schema_version(conn)

    return {"applied": applied, "current_version": current, "migrations_count": len(files)}


def db_health(sqlite_path: str) -> dict:
    """Check DB file exists, dir writable, and SELECT 1 works. Returns ok, path, exists, writable_dir (and error on failure)."""
    p = Path(sqlite_path)
    exists = p.exists()
    writable_dir = os.access(str(p.parent), os.W_OK)
    ok = writable_dir
    try:
        conn = sqlite3.connect(p)
        try:
            conn.execute("SELECT 1;")
        finally:
            conn.close()
    except Exception as e:
        ok = False
        return {"ok": False, "error": str(e), "path": str(p), "exists": exists, "writable_dir": writable_dir}

    return {"ok": ok, "path": str(p), "exists": exists, "writable_dir": writable_dir}

