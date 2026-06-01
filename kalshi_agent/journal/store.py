"""SQLite-backed trade journal.

This is the asset that compounds. Every trade you log captures not just the
numbers but your *reasoning* and the *probability you assigned*. When the market
resolves, you record the outcome. Over time this gives the agent (and you) a
calibrated track record to learn from — which is what turns a generic chatbot
into a personal consultant that knows how *you* trade.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone

SCHEMA = """
CREATE TABLE IF NOT EXISTS trades (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at      TEXT NOT NULL,
    market_ticker   TEXT NOT NULL,
    side            TEXT NOT NULL,          -- 'yes' or 'no'
    entry_price     REAL NOT NULL,          -- cents
    contracts       INTEGER NOT NULL,
    predicted_prob  REAL,                   -- YOUR probability the side pays out
    rationale       TEXT,                   -- why you took it
    status          TEXT NOT NULL DEFAULT 'open',  -- 'open' | 'resolved'
    exit_price      REAL,                   -- cents, if closed before settlement
    outcome         INTEGER,                -- 1 if the side paid out, 0 if not
    pnl_cents       REAL,                   -- realized P&L in cents
    resolved_at     TEXT
);
"""


@dataclass
class Trade:
    id: int | None
    created_at: str
    market_ticker: str
    side: str
    entry_price: float
    contracts: int
    predicted_prob: float | None
    rationale: str | None
    status: str
    exit_price: float | None
    outcome: int | None
    pnl_cents: float | None
    resolved_at: str | None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class JournalStore:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute(SCHEMA)
        self._conn.commit()

    def add_trade(self, market_ticker: str, side: str, entry_price: float,
                  contracts: int, predicted_prob: float | None = None,
                  rationale: str | None = None) -> int:
        cur = self._conn.execute(
            """INSERT INTO trades
               (created_at, market_ticker, side, entry_price, contracts,
                predicted_prob, rationale, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'open')""",
            (_now(), market_ticker, side.lower(), entry_price, contracts,
             predicted_prob, rationale),
        )
        self._conn.commit()
        return int(cur.lastrowid)

    def resolve_trade(self, trade_id: int, outcome: int,
                      exit_price: float | None = None) -> Trade | None:
        """Resolve a trade. outcome=1 if the chosen side paid out, else 0.

        If you held to settlement, P&L is (100 - entry) per contract on a win,
        or -entry on a loss. If you closed early, pass exit_price.
        """
        trade = self.get_trade(trade_id)
        if trade is None:
            return None

        if exit_price is not None:
            pnl = (exit_price - trade.entry_price) * trade.contracts
        elif outcome == 1:
            pnl = (100.0 - trade.entry_price) * trade.contracts
        else:
            pnl = -trade.entry_price * trade.contracts

        self._conn.execute(
            """UPDATE trades
               SET status='resolved', outcome=?, exit_price=?, pnl_cents=?, resolved_at=?
               WHERE id=?""",
            (outcome, exit_price, pnl, _now(), trade_id),
        )
        self._conn.commit()
        return self.get_trade(trade_id)

    def get_trade(self, trade_id: int) -> Trade | None:
        row = self._conn.execute("SELECT * FROM trades WHERE id=?", (trade_id,)).fetchone()
        return _row_to_trade(row) if row else None

    def list_trades(self, status: str | None = None, limit: int = 100) -> list[Trade]:
        if status:
            rows = self._conn.execute(
                "SELECT * FROM trades WHERE status=? ORDER BY id DESC LIMIT ?",
                (status, limit),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM trades ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [_row_to_trade(r) for r in rows]

    def resolved_predictions(self) -> tuple[list[float], list[int]]:
        """Return (predicted_probs, outcomes) for calibration scoring."""
        rows = self._conn.execute(
            """SELECT predicted_prob, outcome FROM trades
               WHERE status='resolved' AND predicted_prob IS NOT NULL AND outcome IS NOT NULL"""
        ).fetchall()
        preds = [float(r["predicted_prob"]) for r in rows]
        outs = [int(r["outcome"]) for r in rows]
        return preds, outs

    def performance_summary(self) -> dict:
        rows = self._conn.execute(
            "SELECT pnl_cents FROM trades WHERE status='resolved' AND pnl_cents IS NOT NULL"
        ).fetchall()
        pnls = [float(r["pnl_cents"]) for r in rows]
        wins = sum(1 for p in pnls if p > 0)
        return {
            "resolved_trades": len(pnls),
            "total_pnl_dollars": round(sum(pnls) / 100.0, 2),
            "win_rate": round(wins / len(pnls), 3) if pnls else None,
            "open_trades": len(self.list_trades(status="open")),
        }

    def close(self) -> None:
        self._conn.close()


def _row_to_trade(row: sqlite3.Row) -> Trade:
    return Trade(**{k: row[k] for k in row.keys()})  # noqa: SIM118
