# Local Setup Guide

## Prerequisites

- Python 3.11+ (`python3 --version` to check — install from [python.org](https://python.org) or `brew install python@3.11` if needed)
- A Kalshi account with an API key pair (see step 3)
- An Anthropic API key from [console.anthropic.com](https://console.anthropic.com)

## 1. Clone the repo

```bash
cd ~/Documents
git clone https://github.com/khimd25/khim-react-router.git
cd khim-react-router
git checkout claude/kalshi-trading-agent-5E6du
```

Then open the folder in Windsurf: **File → Open Folder → ~/Documents/khim-react-router**

## 2. Create the Python environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 3. Set up Kalshi credentials

You need an RSA key pair from Kalshi's dashboard:

1. Log in at [kalshi.com](https://kalshi.com) → Settings → API
2. Create a new API key and **download the private key file**
3. Save the downloaded file as `kalshi_private_key.pem` in the project root

> **Security note:** Never commit this file. It's already listed in `.gitignore`.

## 4. Create your `.env` file

```bash
cp .env.example .env
```

Open `.env` and fill in your credentials:

```
ANTHROPIC_API_KEY=sk-ant-...
KALSHI_KEY_ID=your-key-id-from-kalshi
KALSHI_PRIVATE_KEY_PATH=./kalshi_private_key.pem
KALSHI_API_BASE=https://api.elections.kalshi.com
```

> **Security note:** `.env` is gitignored. Never commit it.

## 5. Verify everything works

```bash
source .venv/bin/activate   # if not already active
python -m kalshi_agent.cli doctor
```

You should see all green checkmarks:
```
✓ ANTHROPIC_API_KEY is set
✓ Kalshi credentials present
✓ private key loads
✓ Kalshi auth works — account balance: $...
✓ live market data — sample: ...
```

## 6. Run the consultant

```bash
python -m kalshi_agent.cli chat
```

Example questions to ask:
- "What open markets have the most edge right now?"
- "The yes price on TICKER is 45c and I think there's a 70% chance it resolves yes — should I trade?"
- "Log a yes trade on TICKER at 55 cents, 10 contracts."
- "Show me my calibration report."

## Other CLI commands

```bash
# List live open markets
python -m kalshi_agent.cli markets

# View your trade journal
python -m kalshi_agent.cli journal list
python -m kalshi_agent.cli journal list --status open
python -m kalshi_agent.cli journal list --status resolved

# Manually log a trade
python -m kalshi_agent.cli journal add TICKER yes 55 10 --prob 0.7 --rationale "my reasoning"

# Resolve a trade (1 = won, 0 = lost)
python -m kalshi_agent.cli journal resolve 1 --outcome 1

# View calibration and P&L stats
python -m kalshi_agent.cli stats
```

## Growing the agent's knowledge

The agent loads everything in the `knowledge/` folder into its system prompt at the start of each session. Add markdown files there to teach it your personal rules, patterns you've noticed, and market context.

```
knowledge/
  strategies.md    ← your risk management rules and trading approach
  market_notes.md  ← observations about specific markets or categories
  *.md             ← add any other topic files you want
```

The more you write here, the more tailored the advice becomes.

## Run tests

```bash
source .venv/bin/activate
pytest tests/ -v
```
