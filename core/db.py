"""SQLite persistence for the application registry.

A fresh connection is opened per operation (cheap with WAL) so the store is safe
to use from FastAPI's threadpool without connection-sharing bugs.
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Iterator

from core import config
from core.models import ApplicationRecord

SCHEMA = """
CREATE TABLE IF NOT EXISTS apps (
    app_id       TEXT PRIMARY KEY,
    name         TEXT NOT NULL,
    version      TEXT NOT NULL,
    path         TEXT NOT NULL,
    runtime_type TEXT NOT NULL,
    trust        TEXT NOT NULL,
    state        TEXT NOT NULL,
    manifest     TEXT NOT NULL,
    port         INTEGER,
    pid          INTEGER,
    registered_at TEXT NOT NULL,
    updated_at   TEXT NOT NULL,
    last_error   TEXT,
    is_builtin   INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(config.db_path(), check_same_thread=False, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with connect() as conn:
        conn.executescript(SCHEMA)


def _row_to_record(row: sqlite3.Row) -> ApplicationRecord:
    return ApplicationRecord(
        app_id=row["app_id"],
        name=row["name"],
        version=row["version"],
        path=row["path"],
        runtime_type=row["runtime_type"],
        trust=row["trust"],
        state=row["state"],
        manifest=json.loads(row["manifest"]),
        port=row["port"],
        pid=row["pid"],
        registered_at=row["registered_at"],
        updated_at=row["updated_at"],
        last_error=row["last_error"],
        is_builtin=bool(row["is_builtin"]),
    )


def upsert_app(record: ApplicationRecord) -> None:
    row = record.to_row()
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO apps (app_id, name, version, path, runtime_type, trust, state,
                              manifest, port, pid, registered_at, updated_at, last_error, is_builtin)
            VALUES (:app_id, :name, :version, :path, :runtime_type, :trust, :state,
                    :manifest, :port, :pid, :registered_at, :updated_at, :last_error, :is_builtin)
            ON CONFLICT(app_id) DO UPDATE SET
                name=excluded.name,
                version=excluded.version,
                path=excluded.path,
                runtime_type=excluded.runtime_type,
                trust=excluded.trust,
                state=excluded.state,
                manifest=excluded.manifest,
                port=excluded.port,
                pid=excluded.pid,
                updated_at=excluded.updated_at,
                last_error=excluded.last_error,
                is_builtin=excluded.is_builtin
            """,
            {**row, "is_builtin": int(record.is_builtin)},
        )


def get_app(app_id: str) -> ApplicationRecord | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM apps WHERE app_id = ?", (app_id,)).fetchone()
    return _row_to_record(row) if row else None


def list_apps() -> list[ApplicationRecord]:
    with connect() as conn:
        rows = conn.execute("SELECT * FROM apps ORDER BY name").fetchall()
    return [_row_to_record(r) for r in rows]


def delete_app(app_id: str) -> bool:
    with connect() as conn:
        cur = conn.execute("DELETE FROM apps WHERE app_id = ?", (app_id,))
    return cur.rowcount > 0


def set_state(app_id: str, state: str, *, port: int | None = None, pid: int | None = None,
              last_error: str | None = None, clear_error: bool = False) -> None:
    fields = ["state = ?", "updated_at = ?"]
    params: list[object] = [state, utcnow()]
    if port is not None:
        fields.append("port = ?")
        params.append(port)
    if pid is not None:
        fields.append("pid = ?")
        params.append(pid)
    if clear_error:
        fields.append("last_error = NULL")
    elif last_error is not None:
        fields.append("last_error = ?")
        params.append(last_error)
    params.append(app_id)
    with connect() as conn:
        conn.execute(f"UPDATE apps SET {', '.join(fields)} WHERE app_id = ?", params)
