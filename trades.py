import sqlite3
from datetime import datetime


DB_PATH = "trades.db"


def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                symbol TEXT,
                side TEXT,
                amount REAL,
                price REAL,
                reason TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                level TEXT,
                title TEXT,
                body TEXT,
                seen INTEGER DEFAULT 0
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                amount REAL NOT NULL,
                entry_price REAL NOT NULL,
                highest_price REAL,
                stop_loss REAL NOT NULL,
                take_profit REAL NOT NULL,
                strategy TEXT,
                opened_at TEXT NOT NULL,
                status TEXT DEFAULT 'open',
                closed_at TEXT,
                close_price REAL,
                close_reason TEXT
            )
        """)
        # Migration: add highest_price to existing DBs
        cols = [r[1] for r in conn.execute("PRAGMA table_info(positions)").fetchall()]
        if "highest_price" not in cols:
            conn.execute("ALTER TABLE positions ADD COLUMN highest_price REAL")
            conn.execute("UPDATE positions SET highest_price = entry_price WHERE highest_price IS NULL")


def log_trade(symbol: str, side: str, amount: float, price: float, reason: str = ""):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO trades (timestamp, symbol, side, amount, price, reason) VALUES (?, ?, ?, ?, ?, ?)",
            (datetime.utcnow().isoformat(), symbol, side, amount, price, reason),
        )


def get_trades() -> list[dict]:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM trades ORDER BY timestamp DESC").fetchall()
        return [dict(r) for r in rows]


def log_notification(title: str, body: str, level: str = "info"):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO notifications (timestamp, level, title, body) VALUES (?, ?, ?, ?)",
            (datetime.utcnow().isoformat(), level, title, body),
        )


def get_notifications(limit: int = 50) -> list[dict]:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM notifications ORDER BY timestamp DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


def mark_notifications_seen():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("UPDATE notifications SET seen = 1 WHERE seen = 0")


def unseen_count() -> int:
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute("SELECT COUNT(*) FROM notifications WHERE seen = 0").fetchone()
        return row[0]


# ---------------------------------------------------------------------------
# Positions
# ---------------------------------------------------------------------------

def open_position(symbol: str, amount: float, entry_price: float,
                  stop_loss: float, take_profit: float, strategy: str) -> int:
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute(
            """INSERT INTO positions
               (symbol, amount, entry_price, highest_price, stop_loss, take_profit, strategy, opened_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (symbol, amount, entry_price, entry_price, stop_loss, take_profit, strategy,
             datetime.utcnow().isoformat()),
        )
        return cur.lastrowid


def update_highest_price(position_id: int, highest_price: float):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "UPDATE positions SET highest_price=? WHERE id=?",
            (highest_price, position_id),
        )


def close_position(position_id: int, close_price: float, close_reason: str):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """UPDATE positions
               SET status='closed', closed_at=?, close_price=?, close_reason=?
               WHERE id=?""",
            (datetime.utcnow().isoformat(), close_price, close_reason, position_id),
        )


def get_open_position(symbol: str) -> dict | None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM positions WHERE symbol=? AND status='open' ORDER BY id DESC LIMIT 1",
            (symbol,),
        ).fetchone()
        return dict(row) if row else None


def get_all_open_positions() -> list[dict]:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM positions WHERE status='open' ORDER BY opened_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def get_closed_positions(limit: int = 50) -> list[dict]:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM positions WHERE status='closed' ORDER BY closed_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]
