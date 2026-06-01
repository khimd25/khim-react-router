from __future__ import annotations

import pytest

from kalshi_agent.analysis.stats import (
    edge,
    evaluate_trade,
    expected_value_cents,
    implied_probability,
    kelly_fraction,
)


class TestImpliedProbability:
    def test_midpoint(self):
        assert implied_probability(50) == 0.5

    def test_low(self):
        assert implied_probability(1) == pytest.approx(0.01)

    def test_high(self):
        assert implied_probability(99) == pytest.approx(0.99)


class TestExpectedValue:
    def test_fair_price(self):
        assert expected_value_cents(0.5, 50) == pytest.approx(0.0)

    def test_positive_ev(self):
        assert expected_value_cents(0.7, 50) == pytest.approx(20.0)

    def test_negative_ev(self):
        assert expected_value_cents(0.3, 50) == pytest.approx(-20.0)


class TestEdge:
    def test_no_edge(self):
        assert edge(0.5, 50) == pytest.approx(0.0)

    def test_positive_edge(self):
        assert edge(0.7, 50) == pytest.approx(0.2)

    def test_negative_edge(self):
        assert edge(0.3, 50) == pytest.approx(-0.2)


class TestKellyFraction:
    def test_no_edge_returns_zero(self):
        assert kelly_fraction(0.5, 50) == pytest.approx(0.0)

    def test_strong_edge(self):
        f = kelly_fraction(0.8, 50)
        assert f > 0
        assert f <= 1.0

    def test_negative_edge_clamped_to_zero(self):
        assert kelly_fraction(0.3, 50) == 0.0

    def test_boundary_price_zero(self):
        assert kelly_fraction(0.5, 0) == 0.0

    def test_boundary_price_100(self):
        assert kelly_fraction(0.5, 100) == 0.0


class TestEvaluateTrade:
    def test_picks_yes_when_underpriced(self):
        ev = evaluate_trade(true_prob_yes=0.8, yes_price_cents=50)
        assert ev.side == "yes"
        assert ev.ev_cents > 0

    def test_picks_no_when_overpriced(self):
        ev = evaluate_trade(true_prob_yes=0.2, yes_price_cents=50)
        assert ev.side == "no"
        assert ev.ev_cents > 0

    def test_half_kelly_default(self):
        ev = evaluate_trade(true_prob_yes=0.8, yes_price_cents=50)
        assert ev.fractional_kelly == pytest.approx(ev.kelly_fraction * 0.5)

    def test_custom_kelly_multiplier(self):
        ev = evaluate_trade(true_prob_yes=0.8, yes_price_cents=50, kelly_multiplier=0.25)
        assert ev.fractional_kelly == pytest.approx(ev.kelly_fraction * 0.25)

    def test_summary_string(self):
        ev = evaluate_trade(true_prob_yes=0.7, yes_price_cents=40)
        s = ev.summary()
        assert "YES" in s
        assert "edge" in s
