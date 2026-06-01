"""Core quantitative tools for evaluating a Kalshi trade.

Kalshi binary contracts trade in CENTS from 1 to 99. A "Yes" contract bought at
price p (cents) pays out 100 cents if the event happens, 0 otherwise. So the
market's implied probability of "Yes" is simply p / 100.

The whole game is: form your own probability estimate q, compare it to the
market's implied probability p/100, and size your position by your edge.
"""

from __future__ import annotations

from dataclasses import dataclass


def implied_probability(price_cents: float) -> float:
    """Market-implied probability from a contract price in cents (1-99)."""
    return price_cents / 100.0


def expected_value_cents(true_prob: float, price_cents: float) -> float:
    """EV per contract, in cents, of buying at `price_cents` given your `true_prob`.

    Win  (prob q):  +(100 - price)
    Lose (prob 1-q): -price
    EV = q*(100 - price) - (1-q)*price = 100*q - price
    """
    return 100.0 * true_prob - price_cents


def edge(true_prob: float, price_cents: float) -> float:
    """Your edge in probability points (e.g. 0.07 = 7 points of edge)."""
    return true_prob - implied_probability(price_cents)


def kelly_fraction(true_prob: float, price_cents: float) -> float:
    """Fraction of bankroll to stake per the Kelly criterion for a Yes buy.

    Net odds b = (payout - cost) / cost = (100 - price) / price.
    Kelly f* = (q*b - (1-q)) / b, clamped to [0, 1]. A negative result means
    no edge on the Yes side (consider the No side instead).
    """
    if not 0 < price_cents < 100:
        return 0.0
    b = (100.0 - price_cents) / price_cents
    q = true_prob
    f = (q * b - (1.0 - q)) / b
    return max(0.0, min(1.0, f))


@dataclass
class TradeEvaluation:
    side: str               # "yes" or "no"
    price_cents: float      # price you'd pay for that side
    true_prob: float        # your probability the side pays out
    implied_prob: float
    edge: float
    ev_cents: float
    kelly_fraction: float
    fractional_kelly: float  # half-Kelly, the usual practical stake

    def summary(self) -> str:
        return (
            f"{self.side.upper()} @ {self.price_cents:.0f}c | "
            f"your p={self.true_prob:.2%} vs implied {self.implied_prob:.2%} | "
            f"edge {self.edge:+.2%} | EV {self.ev_cents:+.1f}c/contract | "
            f"Kelly {self.kelly_fraction:.1%} (half {self.fractional_kelly:.1%})"
        )


def evaluate_trade(true_prob_yes: float, yes_price_cents: float,
                   kelly_multiplier: float = 0.5) -> TradeEvaluation:
    """Evaluate the better side (Yes or No) given your probability estimate.

    `true_prob_yes` is YOUR estimate that the event resolves Yes.
    `yes_price_cents` is the current Yes ask. The No price is 100 - yes price.
    Returns the side with positive edge (or the Yes side if neither).
    """
    yes_eval = _eval_side("yes", true_prob_yes, yes_price_cents, kelly_multiplier)
    no_eval = _eval_side("no", 1.0 - true_prob_yes, 100.0 - yes_price_cents, kelly_multiplier)
    return yes_eval if yes_eval.ev_cents >= no_eval.ev_cents else no_eval


def _eval_side(side: str, true_prob: float, price_cents: float,
               kelly_multiplier: float) -> TradeEvaluation:
    k = kelly_fraction(true_prob, price_cents)
    return TradeEvaluation(
        side=side,
        price_cents=price_cents,
        true_prob=true_prob,
        implied_prob=implied_probability(price_cents),
        edge=edge(true_prob, price_cents),
        ev_cents=expected_value_cents(true_prob, price_cents),
        kelly_fraction=k,
        fractional_kelly=k * kelly_multiplier,
    )
