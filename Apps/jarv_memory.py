#!/usr/bin/env python3
"""
jarvis_memory.py — SQLite long-term memory for Jarvis

Features
- Full storage of BOTH user + assistant messages (role-separated)
- "remembered" items (explicit memory) vs normal chat turns
- Soft-delete for "forget" (doesn't physically remove rows)
- Simple retrieval helpers: recent, search, dump
- Optional CLI for testing:
    python3 jarvis_memory.py --db ~/.jarvis/jarvis_memory.db --user JD add --role user "hello"
    python3 jarvis_memory.py --db ~/.jarvis/jarvis_memory.db --user JD recent --n 20
    python3 jarvis_memory.py --db ~/.jarvis/jarvis_memory.db --user JD forget-keyword "password"
"""

from __future__ import annotations

import argparse
import os
import sqlite3
from dataclasses import dataclass
from typing import List, Optional, Tuple


SCHEMA_VERSION = 1


@dataclass(frozen=True)
class MemoryRow:
    id: int
    user_id: str
    role: str
    content: str
    kind: str
    deleted: int
    timestamp: str


class JarvisMemory:
    """
    SQLite-backed memory store.

    Table: conversations
      - id (pk)
      - user_id
      - role: 'user' | 'assistant' | 'system'
      - content
      - kind: 'chat' | 'remembered'
      - deleted: 0/1 (soft delete)
      - timestamp (sqlite CURRENT_TIMESTAMP)
    """

    def __init__(self, db_path: str = "~/.jarvis/jarvis_memory.db"):
        self.db_path = os.path.expanduser(db_path)
        self._ensure_parent_dir()
        self._init_database()
        self._attempt_migrate_legacy_schema()

    def _ensure_parent_dir(self) -> None:
        parent = os.path.dirname(self.db_path)
        if parent and not os.path.isdir(parent):
            os.makedirs(parent, exist_ok=True)

    def _connect(self) -> sqlite3.Connection:
        # WAL improves concurrent read/write and durability for CLI usage
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.row_factory = sqlite3.Row
        return conn

    def _init_database(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    kind TEXT DEFAULT 'chat',
                    deleted INTEGER DEFAULT 0,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_conv_user_time
                ON conversations(user_id, id)
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_conv_user_deleted
                ON conversations(user_id, deleted)
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_conv_content
                ON conversations(content)
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS meta (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
                """
            )
            conn.execute(
                "INSERT OR IGNORE INTO meta(key, value) VALUES('schema_version', ?)",
                (str(SCHEMA_VERSION),),
            )

    # --- Legacy migration (from your old schema) ------------------------------
    # Old table: conversations(user_id, message, timestamp, context)
    # We try to detect it and migrate into the new columns.
    def _attempt_migrate_legacy_schema(self) -> None:
        with self._connect() as conn:
            # If "content" column exists, we're already on the new schema.
            cols = self._table_columns(conn, "conversations")
            if not cols:
                return

            if "content" in cols and "role" in cols:
                return  # new schema already

            # Legacy detection: has "message" and "context"
            if "message" in cols and "context" in cols:
                # Add new columns if missing
                if "role" not in cols:
                    conn.execute("ALTER TABLE conversations ADD COLUMN role TEXT;")
                if "content" not in cols:
                    conn.execute("ALTER TABLE conversations ADD COLUMN content TEXT;")
                if "kind" not in cols:
                    conn.execute("ALTER TABLE conversations ADD COLUMN kind TEXT DEFAULT 'chat';")
                if "deleted" not in cols:
                    conn.execute("ALTER TABLE conversations ADD COLUMN deleted INTEGER DEFAULT 0;")

                # Populate new columns from legacy data
                # - content <- message
                # - role <- context if it matches known roles, else 'user'
                # - kind <- if context says remembered, set 'remembered'
                # We keep your original timestamp column if it exists.
                conn.execute(
                    """
                    UPDATE conversations
                    SET content = COALESCE(content, message)
                    WHERE content IS NULL
                    """
                )
                conn.execute(
                    """
                    UPDATE conversations
                    SET role =
                        CASE
                            WHEN lower(COALESCE(context, '')) IN ('user','assistant','system')
                                THEN lower(context)
                            WHEN lower(COALESCE(context, '')) IN ('remembered','memory','note')
                                THEN 'user'
                            ELSE 'user'
                        END
                    WHERE role IS NULL
                    """
                )
                conn.execute(
                    """
                    UPDATE conversations
                    SET kind =
                        CASE
                            WHEN lower(COALESCE(context, '')) IN ('remembered','memory','note')
                                THEN 'remembered'
                            ELSE COALESCE(kind, 'chat')
                        END
                    """
                )

                # Ensure role/content NOT NULL going forward
                # (SQLite can't easily add NOT NULL constraints; we just enforce in code.)
                conn.execute(
                    "UPDATE meta SET value=? WHERE key='schema_version'",
                    (str(SCHEMA_VERSION),),
                )
                conn.commit()

    @staticmethod
    def _table_columns(conn: sqlite3.Connection, table: str) -> List[str]:
        try:
            rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
            return [r["name"] for r in rows]
        except sqlite3.Error:
            return []

    # --- Public API -----------------------------------------------------------

    def store_message(self, user_id: str, role: str, content: str, kind: str = "chat") -> int:
        """
        Store a message. Returns inserted row id.
        role: 'user' | 'assistant' | 'system'
        kind: 'chat' | 'remembered'
        """
        role = (role or "").strip().lower()
        if role not in {"user", "assistant", "system"}:
            raise ValueError("role must be one of: user, assistant, system")

        kind = (kind or "chat").strip().lower()
        if kind not in {"chat", "remembered"}:
            raise ValueError("kind must be one of: chat, remembered")

        content = (content or "").strip()
        if not content:
            raise ValueError("content cannot be empty")

        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO conversations (user_id, role, content, kind, deleted)
                VALUES (?, ?, ?, ?, 0)
                """,
                (user_id, role, content, kind),
            )
            conn.commit()
            return int(cur.lastrowid)

    def remember(self, user_id: str, content: str) -> int:
        """Convenience: store an explicit memory item."""
        return self.store_message(user_id=user_id, role="user", content=content, kind="remembered")

    def get_recent(
        self,
        user_id: str,
        limit: int = 30,
        include_deleted: bool = False,
        kind: Optional[str] = None,
    ) -> List[MemoryRow]:
        """
        Return recent rows (newest first).
        kind: None | 'chat' | 'remembered'
        """
        limit = max(1, int(limit))
        where = ["user_id = ?"]
        params: List[object] = [user_id]

        if not include_deleted:
            where.append("deleted = 0")

        if kind:
            k = kind.strip().lower()
            if k not in {"chat", "remembered"}:
                raise ValueError("kind must be one of: chat, remembered")
            where.append("kind = ?")
            params.append(k)

        sql = f"""
            SELECT id, user_id, role, content, kind, deleted, timestamp
            FROM conversations
            WHERE {" AND ".join(where)}
            ORDER BY id DESC
            LIMIT ?
        """
        params.append(limit)

        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()

        return [
            MemoryRow(
                id=int(r["id"]),
                user_id=str(r["user_id"]),
                role=str(r["role"]),
                content=str(r["content"]),
                kind=str(r["kind"]),
                deleted=int(r["deleted"]),
                timestamp=str(r["timestamp"]),
            )
            for r in rows
        ]

    def search(
        self,
        user_id: str,
        query: str,
        limit: int = 20,
        include_deleted: bool = False,
        kind: Optional[str] = None,
    ) -> List[MemoryRow]:
        """
        LIKE search over content, newest first.
        """
        q = (query or "").strip()
        if not q:
            return []

        limit = max(1, int(limit))
        where = ["user_id = ?", "content LIKE ?"]
        params: List[object] = [user_id, f"%{q}%"]

        if not include_deleted:
            where.append("deleted = 0")

        if kind:
            k = kind.strip().lower()
            if k not in {"chat", "remembered"}:
                raise ValueError("kind must be one of: chat, remembered")
            where.append("kind = ?")
            params.append(k)

        sql = f"""
            SELECT id, user_id, role, content, kind, deleted, timestamp
            FROM conversations
            WHERE {" AND ".join(where)}
            ORDER BY id DESC
            LIMIT ?
        """
        params.append(limit)

        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()

        return [
            MemoryRow(
                id=int(r["id"]),
                user_id=str(r["user_id"]),
                role=str(r["role"]),
                content=str(r["content"]),
                kind=str(r["kind"]),
                deleted=int(r["deleted"]),
                timestamp=str(r["timestamp"]),
            )
            for r in rows
        ]

    def forget_keyword(self, user_id: str, keyword: str) -> int:
        """
        Soft-delete all rows whose content LIKE %keyword% for a user.
        Returns number of affected rows.
        """
        kw = (keyword or "").strip()
        if not kw:
            return 0

        with self._connect() as conn:
            cur = conn.execute(
                """
                UPDATE conversations
                SET deleted = 1
                WHERE user_id = ? AND deleted = 0 AND content LIKE ?
                """,
                (user_id, f"%{kw}%"),
            )
            conn.commit()
            return int(cur.rowcount)

    def forget_id(self, user_id: str, row_id: int) -> int:
        """Soft-delete a specific row id for a user. Returns 1 if deleted, else 0."""
        with self._connect() as conn:
            cur = conn.execute(
                """
                UPDATE conversations
                SET deleted = 1
                WHERE user_id = ? AND id = ? AND deleted = 0
                """,
                (user_id, int(row_id)),
            )
            conn.commit()
            return int(cur.rowcount)

    def clear_user(self, user_id: str) -> int:
        """Soft-delete all rows for a user. Returns number of affected rows."""
        with self._connect() as conn:
            cur = conn.execute(
                """
                UPDATE conversations
                SET deleted = 1
                WHERE user_id = ? AND deleted = 0
                """,
                (user_id,),
            )
            conn.commit()
            return int(cur.rowcount)

    def vacuum(self) -> None:
        """
        Run VACUUM. (Only really useful if you physically delete rows; soft-delete doesn't shrink DB.)
        """
        with self._connect() as conn:
            conn.execute("VACUUM;")
            conn.commit()


# --- Optional CLI ------------------------------------------------------------

def _cmd_add(mem: JarvisMemory, user: str, role: str, kind: str, content: str) -> None:
    row_id = mem.store_message(user_id=user, role=role, content=content, kind=kind)
    print(f"added id={row_id}")


def _cmd_recent(mem: JarvisMemory, user: str, n: int, kind: Optional[str], include_deleted: bool) -> None:
    rows = mem.get_recent(user_id=user, limit=n, kind=kind, include_deleted=include_deleted)
    rows = list(reversed(rows))  # print oldest -> newest for readability
    for r in rows:
        flag = " (DELETED)" if r.deleted else ""
        print(f"[{r.id}] {r.timestamp} {r.role}/{r.kind}{flag}: {r.content}")


def _cmd_search(mem: JarvisMemory, user: str, q: str, n: int, kind: Optional[str], include_deleted: bool) -> None:
    rows = mem.search(user_id=user, query=q, limit=n, kind=kind, include_deleted=include_deleted)
    rows = list(reversed(rows))
    for r in rows:
        flag = " (DELETED)" if r.deleted else ""
        print(f"[{r.id}] {r.timestamp} {r.role}/{r.kind}{flag}: {r.content}")


def _cmd_forget_keyword(mem: JarvisMemory, user: str, kw: str) -> None:
    n = mem.forget_keyword(user_id=user, keyword=kw)
    print(f"forgot {n} row(s) matching: {kw}")


def _cmd_forget_id(mem: JarvisMemory, user: str, row_id: int) -> None:
    n = mem.forget_id(user_id=user, row_id=row_id)
    print(f"forgot {n} row(s) with id={row_id}")


def _cmd_clear(mem: JarvisMemory, user: str) -> None:
    n = mem.clear_user(user_id=user)
    print(f"cleared {n} row(s) for user={user}")


def main() -> None:
    p = argparse.ArgumentParser(description="Jarvis SQLite memory helper")
    p.add_argument("--db", default="~/.jarvis/jarvis_memory.db", help="SQLite DB path")
    p.add_argument("--user", default=os.getenv("JARVIS_USER_ID", "JD"), help="User id namespace")

    sub = p.add_subparsers(dest="cmd", required=True)

    add = sub.add_parser("add", help="Add a row")
    add.add_argument("--role", default="user", choices=["user", "assistant", "system"])
    add.add_argument("--kind", default="chat", choices=["chat", "remembered"])
    add.add_argument("content", nargs="+", help="Content text")

    recent = sub.add_parser("recent", help="Show recent rows")
    recent.add_argument("--n", type=int, default=20)
    recent.add_argument("--kind", default=None, choices=[None, "chat", "remembered"])
    recent.add_argument("--include-deleted", action="store_true")

    search = sub.add_parser("search", help="Search rows (LIKE)")
    search.add_argument("query", nargs="+")
    search.add_argument("--n", type=int, default=20)
    search.add_argument("--kind", default=None, choices=[None, "chat", "remembered"])
    search.add_argument("--include-deleted", action="store_true")

    fk = sub.add_parser("forget-keyword", help="Soft-delete rows containing keyword")
    fk.add_argument("keyword", nargs="+", help="Keyword to match in content")

    fid = sub.add_parser("forget-id", help="Soft-delete a row by id")
    fid.add_argument("row_id", type=int)

    clr = sub.add_parser("clear", help="Soft-delete all rows for user")

    args = p.parse_args()
    mem = JarvisMemory(db_path=args.db)

    if args.cmd == "add":
        _cmd_add(mem, args.user, args.role, args.kind, " ".join(args.content))
    elif args.cmd == "recent":
        _cmd_recent(mem, args.user, args.n, args.kind, args.include_deleted)
    elif args.cmd == "search":
        _cmd_search(mem, args.user, " ".join(args.query), args.n, args.kind, args.include_deleted)
    elif args.cmd == "forget-keyword":
        _cmd_forget_keyword(mem, args.user, " ".join(args.keyword))
    elif args.cmd == "forget-id":
        _cmd_forget_id(mem, args.user, args.row_id)
    elif args.cmd == "clear":
        _cmd_clear(mem, args.user)
    else:
        raise SystemExit("unknown command")


if __name__ == "__main__":
    main()
