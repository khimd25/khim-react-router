"""The Claude-powered consultant.

Uses the Anthropic SDK's tool runner: we define tools as plain functions, and
the SDK handles the agentic loop (call Claude -> run a tool -> feed the result
back -> repeat) until Claude has a final answer. Claude reaches for live Kalshi
data and your journal on its own.

Model: Opus 4.8 with adaptive thinking. The system prompt is prompt-cached so
repeated turns are cheap.
"""

from __future__ import annotations

import json

import anthropic
from anthropic import beta_tool

from ..analysis import calibration, stats
from .prompts import build_system_prompt

# Tools are module-level functions (so @beta_tool can introspect them), but they
# need access to the live client and journal. We stash those here at runtime.
_CTX: dict = {"client": None, "journal": None}


# ---------------------------------------------------------------------------
# Tools exposed to Claude
# ---------------------------------------------------------------------------

@beta_tool
def get_markets(status: str = "open", limit: int = 20) -> str:
    """List Kalshi markets with their current prices.

    Args:
        status: Market status filter: open, closed, settled, or unopened.
        limit: Max number of markets to return (1-100).
    """
    data = _CTX["client"].get_markets(status=status, limit=limit)
    markets = [
        {
            "ticker": m.get("ticker"),
            "title": m.get("title"),
            "yes_bid": m.get("yes_bid"),
            "yes_ask": m.get("yes_ask"),
            "last_price": m.get("last_price"),
            "volume": m.get("volume"),
            "close_time": m.get("close_time"),
        }
        for m in data.get("markets", [])
    ]
    return json.dumps(markets)


@beta_tool
def get_market(ticker: str) -> str:
    """Get full detail for one market (price, volume, rules, close time).

    Args:
        ticker: The market ticker, e.g. 'KXPRES-24-DT'.
    """
    return json.dumps(_CTX["client"].get_market(ticker).get("market", {}))


@beta_tool
def get_orderbook(ticker: str) -> str:
    """Get the current order book (bid/ask depth) for a market.

    Args:
        ticker: The market ticker.
    """
    return json.dumps(_CTX["client"].get_orderbook(ticker).get("orderbook", {}))


@beta_tool
def get_balance() -> str:
    """Get the user's current Kalshi account balance (requires API credentials)."""
    return json.dumps(_CTX["client"].get_balance())


@beta_tool
def get_positions() -> str:
    """Get the user's current open positions on Kalshi (requires credentials)."""
    return json.dumps(_CTX["client"].get_positions())


@beta_tool
def evaluate_trade(true_prob_yes: float, yes_price_cents: float) -> str:
    """Compute edge, expected value, and Kelly position size for a trade.

    Args:
        true_prob_yes: YOUR estimated probability (0-1) the market resolves Yes.
        yes_price_cents: The current Yes price in cents (1-99).
    """
    ev = stats.evaluate_trade(true_prob_yes, yes_price_cents)
    return json.dumps({
        "recommended_side": ev.side,
        "price_cents": ev.price_cents,
        "your_probability": ev.true_prob,
        "implied_probability": ev.implied_prob,
        "edge": ev.edge,
        "ev_cents_per_contract": ev.ev_cents,
        "full_kelly_fraction": ev.kelly_fraction,
        "half_kelly_fraction": ev.fractional_kelly,
        "summary": ev.summary(),
    })


@beta_tool
def log_trade(market_ticker: str, side: str, entry_price: float, contracts: int,
              predicted_prob: float, rationale: str) -> str:
    """Record a trade in the user's journal so it can be scored later.

    Args:
        market_ticker: The market ticker.
        side: 'yes' or 'no'.
        entry_price: Price paid in cents.
        contracts: Number of contracts.
        predicted_prob: The probability (0-1) you assigned to this side paying out.
        rationale: Short note on why you took the trade.
    """
    trade_id = _CTX["journal"].add_trade(
        market_ticker, side, entry_price, contracts, predicted_prob, rationale,
    )
    return json.dumps({"logged_trade_id": trade_id})


@beta_tool
def list_trades(status: str = "all") -> str:
    """List trades from the journal.

    Args:
        status: 'open', 'resolved', or 'all'.
    """
    s = None if status == "all" else status
    trades = _CTX["journal"].list_trades(status=s, limit=50)
    return json.dumps([
        {k: v for k, v in t.__dict__.items()} for t in trades
    ])


@beta_tool
def calibration_report() -> str:
    """Report the user's forecasting accuracy (Brier score + calibration table)."""
    preds, outs = _CTX["journal"].resolved_predictions()
    return calibration.report(preds, outs)


ALL_TOOLS = [
    get_markets, get_market, get_orderbook, get_balance, get_positions,
    evaluate_trade, log_trade, list_trades, calibration_report,
]


# ---------------------------------------------------------------------------
# Consultant
# ---------------------------------------------------------------------------

class Consultant:
    def __init__(self, client, journal, knowledge_dir: str,
                 model: str = "claude-opus-4-8", anthropic_api_key: str | None = None) -> None:
        _CTX["client"] = client
        _CTX["journal"] = journal
        self.model = model
        self._anthropic = anthropic.Anthropic(api_key=anthropic_api_key)
        self._system = build_system_prompt(knowledge_dir)
        self._messages: list[dict] = []

    def ask(self, user_message: str) -> str:
        """Send one user turn; run tools as needed; return Claude's final text."""
        self._messages.append({"role": "user", "content": user_message})

        runner = self._anthropic.beta.messages.tool_runner(
            model=self.model,
            max_tokens=16000,
            thinking={"type": "adaptive"},
            output_config={"effort": "high"},
            # System prompt is cached so multi-turn chat stays cheap.
            system=[{
                "type": "text",
                "text": self._system,
                "cache_control": {"type": "ephemeral"},
            }],
            tools=ALL_TOOLS,
            messages=self._messages,
        )

        final_text = ""
        for message in runner:
            for block in message.content:
                if block.type == "text":
                    final_text = block.text

        # Keep conversational continuity. (We persist the final text; tool_use
        # detail lives in the runner's internal transcript for this turn.)
        self._messages.append({"role": "assistant", "content": final_text})
        return final_text
