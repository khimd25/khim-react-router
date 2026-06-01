"""Score how good your probability estimates actually are over time.

This is the feedback loop that makes the agent improve: every time you log a
prediction and later record the real outcome, we can measure your calibration.
A perfectly calibrated forecaster who says "70%" is right 70% of the time.

- Brier score: mean squared error of probabilistic forecasts. Lower is better.
  0.0 = perfect, 0.25 = no better than always guessing 50%.
- Calibration table: bucket predictions by confidence and compare predicted
  probability to actual hit rate in each bucket.
"""

from __future__ import annotations

from dataclasses import dataclass


def brier_score(predictions: list[float], outcomes: list[int]) -> float:
    """Mean squared error between predicted probs and binary outcomes (0/1)."""
    if not predictions:
        return float("nan")
    if len(predictions) != len(outcomes):
        raise ValueError("predictions and outcomes must be the same length")
    return sum((p - o) ** 2 for p, o in zip(predictions, outcomes)) / len(predictions)


@dataclass
class CalibrationBin:
    low: float
    high: float
    count: int
    mean_predicted: float
    actual_rate: float

    def line(self) -> str:
        return (
            f"  {self.low:.0%}-{self.high:.0%}: n={self.count:<3d} "
            f"predicted={self.mean_predicted:.0%} actual={self.actual_rate:.0%}"
        )


def calibration_table(predictions: list[float], outcomes: list[int],
                      n_bins: int = 5) -> list[CalibrationBin]:
    """Group predictions into equal-width confidence bins and compare."""
    bins: list[CalibrationBin] = []
    width = 1.0 / n_bins
    for i in range(n_bins):
        low, high = i * width, (i + 1) * width
        # Include the top edge in the last bin.
        in_bin = [
            (p, o) for p, o in zip(predictions, outcomes)
            if (low <= p < high) or (i == n_bins - 1 and p == high)
        ]
        if not in_bin:
            continue
        ps = [p for p, _ in in_bin]
        os = [o for _, o in in_bin]
        bins.append(CalibrationBin(
            low=low,
            high=high,
            count=len(in_bin),
            mean_predicted=sum(ps) / len(ps),
            actual_rate=sum(os) / len(os),
        ))
    return bins


def report(predictions: list[float], outcomes: list[int]) -> str:
    """Human-readable calibration report."""
    if not predictions:
        return "No resolved predictions yet — log trades with a predicted probability and resolve them to build a track record."
    lines = [
        f"Resolved predictions: {len(predictions)}",
        f"Brier score: {brier_score(predictions, outcomes):.4f}  (lower is better; 0.25 = coin flip)",
        "Calibration (predicted vs actual hit rate):",
    ]
    for b in calibration_table(predictions, outcomes):
        lines.append(b.line())
    return "\n".join(lines)
