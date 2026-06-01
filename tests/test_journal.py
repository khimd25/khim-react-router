from __future__ import annotations

import pytest

from kalshi_agent.journal.store import JournalStore


@pytest.fixture()
def journal(tmp_path):
    j = JournalStore(str(tmp_path / "test.db"))
    yield j
    j.close()


class TestAddAndGet:
    def test_add_returns_id(self, journal):
        tid = journal.add_trade("TICKER-1", "yes", 55, 10)
        assert tid >= 1

    def test_get_trade(self, journal):
        tid = journal.add_trade("TICKER-2", "no", 40, 5, predicted_prob=0.65, rationale="test")
        t = journal.get_trade(tid)
        assert t is not None
        assert t.market_ticker == "TICKER-2"
        assert t.side == "no"
        assert t.entry_price == 40
        assert t.contracts == 5
        assert t.predicted_prob == 0.65
        assert t.status == "open"

    def test_get_missing_returns_none(self, journal):
        assert journal.get_trade(9999) is None


class TestResolve:
    def test_win_pnl(self, journal):
        tid = journal.add_trade("T", "yes", 60, 2)
        t = journal.resolve_trade(tid, outcome=1)
        assert t.status == "resolved"
        assert t.outcome == 1
        assert t.pnl_cents == pytest.approx((100 - 60) * 2)

    def test_loss_pnl(self, journal):
        tid = journal.add_trade("T", "yes", 60, 2)
        t = journal.resolve_trade(tid, outcome=0)
        assert t.pnl_cents == pytest.approx(-60 * 2)

    def test_early_exit(self, journal):
        tid = journal.add_trade("T", "yes", 40, 3)
        t = journal.resolve_trade(tid, outcome=1, exit_price=70)
        assert t.pnl_cents == pytest.approx((70 - 40) * 3)

    def test_resolve_missing(self, journal):
        assert journal.resolve_trade(9999, outcome=1) is None


class TestList:
    def test_list_all(self, journal):
        journal.add_trade("A", "yes", 50, 1)
        journal.add_trade("B", "no", 60, 2)
        assert len(journal.list_trades()) == 2

    def test_filter_by_status(self, journal):
        t1 = journal.add_trade("A", "yes", 50, 1)
        journal.add_trade("B", "no", 60, 2)
        journal.resolve_trade(t1, outcome=1)
        assert len(journal.list_trades(status="open")) == 1
        assert len(journal.list_trades(status="resolved")) == 1


class TestCalibrationData:
    def test_resolved_predictions(self, journal):
        t1 = journal.add_trade("A", "yes", 50, 1, predicted_prob=0.7)
        t2 = journal.add_trade("B", "yes", 50, 1, predicted_prob=0.3)
        journal.resolve_trade(t1, outcome=1)
        journal.resolve_trade(t2, outcome=0)
        preds, outs = journal.resolved_predictions()
        assert len(preds) == 2
        assert set(outs) == {0, 1}

    def test_skips_trades_without_prediction(self, journal):
        t1 = journal.add_trade("A", "yes", 50, 1)
        journal.resolve_trade(t1, outcome=1)
        preds, _outs = journal.resolved_predictions()
        assert len(preds) == 0


class TestPerformanceSummary:
    def test_empty(self, journal):
        perf = journal.performance_summary()
        assert perf["resolved_trades"] == 0
        assert perf["win_rate"] is None

    def test_with_trades(self, journal):
        t1 = journal.add_trade("A", "yes", 50, 1)
        t2 = journal.add_trade("B", "yes", 50, 1)
        journal.resolve_trade(t1, outcome=1)
        journal.resolve_trade(t2, outcome=0)
        perf = journal.performance_summary()
        assert perf["resolved_trades"] == 2
        assert perf["win_rate"] == pytest.approx(0.5)
        assert perf["total_pnl_dollars"] == pytest.approx((50 - 50) / 100)
