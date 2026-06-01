# Kalshi Trading Consultant

A personal, AI-powered trading consultant for [Kalshi](https://kalshi.com) that
you grow over time. It pairs Claude (the reasoning "brain") with live Kalshi
market data, a quantitative analysis engine, and a trade journal that compounds
into a calibrated record of how *you* trade.

> **Not financial advice.** This is a decision-support tool for your own
> informed trading. You make every trade decision and place every order
> yourself — the agent never trades on your behalf.

## What it does

- **Chat consultant** — ask about any market; the agent pulls *live* prices and
  order books, forms a probability estimate, computes your edge / EV / Kelly
  size, and gives a clear recommendation with the reasoning and risks.
- **Stats engine** — implied probability, expected value, Kelly position sizing,
  Brier score, and calibration of your past predictions.
- **Trade journal** — log every trade with the probability you assigned and your
  rationale; resolve them later to score your forecasting accuracy.
- **Knowledge base** — `knowledge/*.md` files become part of the agent's system
  prompt, so it gets smarter about your markets as you add notes.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env        # then fill in your keys
```

You need:
1. An **Anthropic API key** (`ANTHROPIC_API_KEY`).
2. **Kalshi API credentials** — create an API key in Kalshi's web UI (Settings →
   API), download the RSA private key PEM, and set `KALSHI_KEY_ID` +
   `KALSHI_PRIVATE_KEY_PATH`. Start on the **demo host** (`KALSHI_API_BASE`).

## Usage

```bash
# Interactive consultant
python -m kalshi_agent.cli chat

# Browse live markets
python -m kalshi_agent.cli markets --status open --limit 20

# Journal: log a trade, then resolve it after settlement
python -m kalshi_agent.cli journal add KXMARKET-TICKER yes 62 10 --prob 0.70 --rationale "model says ~70%"
python -m kalshi_agent.cli journal list
python -m kalshi_agent.cli journal resolve 1 --outcome 1

# Your calibration + P&L
python -m kalshi_agent.cli stats
```

## How to grow it

This is a foundation designed to expand. The highest-leverage next steps:

1. **Feed the journal.** Log every trade with a probability and rationale. After
   ~30 resolved trades, `stats` starts revealing whether you're systematically
   over- or under-confident — and the agent can correct for it.
2. **Edit `knowledge/*.md`.** Anything you learn about a market category goes
   here and becomes part of the agent's reasoning on every turn.
3. **Tune `kalshi_agent/agent/prompts.py`.** As you learn what good advice looks
   like for you, refine the system prompt.
4. **Add tools.** New analytical capabilities (backtesting, news ingestion,
   correlation across markets) slot in as `@beta_tool` functions in
   `kalshi_agent/agent/consultant.py`.

## Architecture

```
kalshi_agent/
  config.py              # env + base URLs
  kalshi/auth.py         # RSA-PSS request signing
  kalshi/client.py       # live Kalshi REST client
  analysis/stats.py      # implied prob, EV, edge, Kelly
  analysis/calibration.py# Brier score + calibration
  journal/store.py       # SQLite trade journal
  agent/prompts.py       # the system prompt (tune over time)
  agent/consultant.py    # Claude (Opus 4.8) + tools
  cli.py                 # entry point
knowledge/               # your evolving market notes (in the system prompt)
```
