from __future__ import annotations

import math

import pytest

from kalshi_agent.analysis.calibration import (
    brier_score,
    calibration_table,
    report,
)


class TestBrierScore:
    def test_perfect(self):
        assert brier_score([1.0, 0.0], [1, 0]) == pytest.approx(0.0)

    def test_worst(self):
        assert brier_score([1.0, 0.0], [0, 1]) == pytest.approx(1.0)

    def test_coin_flip(self):
        assert brier_score([0.5, 0.5], [1, 0]) == pytest.approx(0.25)

    def test_empty_returns_nan(self):
        assert math.isnan(brier_score([], []))

    def test_length_mismatch_raises(self):
        with pytest.raises(ValueError):
            brier_score([0.5], [1, 0])


class TestCalibrationTable:
    def test_all_in_one_bin(self):
        preds = [0.5, 0.55, 0.52]
        outs = [1, 0, 1]
        bins = calibration_table(preds, outs, n_bins=5)
        assert len(bins) == 1
        assert bins[0].count == 3

    def test_bins_cover_range(self):
        preds = [0.1, 0.3, 0.5, 0.7, 0.9]
        outs = [0, 0, 1, 1, 1]
        bins = calibration_table(preds, outs, n_bins=5)
        assert len(bins) == 5

    def test_empty_bins_skipped(self):
        preds = [0.1, 0.9]
        outs = [0, 1]
        bins = calibration_table(preds, outs, n_bins=5)
        assert len(bins) == 2

    def test_bin_line_format(self):
        preds = [0.5, 0.55]
        outs = [1, 1]
        bins = calibration_table(preds, outs, n_bins=5)
        line = bins[0].line()
        assert "predicted=" in line
        assert "actual=" in line


class TestReport:
    def test_no_predictions(self):
        r = report([], [])
        assert "No resolved predictions" in r

    def test_with_predictions(self):
        r = report([0.7, 0.7, 0.7], [1, 1, 0])
        assert "Brier score" in r
        assert "Calibration" in r
