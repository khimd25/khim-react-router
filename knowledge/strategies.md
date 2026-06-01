# Strategies & rules

Your personal trading rules. The agent will follow these when advising you.

## Risk rules

- Default position size: half-Kelly or smaller.
- Max bankroll on any single market: ___%.
- Don't trade markets with volume below: ___.
- Avoid markets within ___ hours of settlement unless there's a clear edge.

## Process

- Always form an independent probability estimate BEFORE looking at the price,
  when possible, to avoid anchoring.
- Log every trade with the probability you assigned and a one-line rationale.
- Review calibration weekly (`python -m kalshi_agent.cli stats`).
