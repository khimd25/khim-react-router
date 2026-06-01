# Project Handoff — Kalshi Trading Consultant

> A handoff document for another AI agent (or developer) picking up this project.
> Last updated by the previous session on the `claude/kalshi-trading-agent-5E6du` branch.

---

## 1. What this project is

A **personal AI trading consultant for [Kalshi](https://kalshi.com)** (a regulated
event-contract / prediction-market exchange). It is a **Python CLI** that the owner
talks to like a chatbot. Three capabilities, by design kept separate:

1. **A quantitative engine** — edge, expected value, Kelly sizing, Brier score, calibration.
2. **A growing knowledge base** — plain markdown files the owner edits over time; folded into the system prompt.
3. **An AI consultant** — Claude (Opus 4.8) with live Kalshi API access and tools, driven by the Anthropic SDK tool runner.

The intent is a tool that **compounds**: every trade is logged with the probability the
owner assigned, so over time the agent can score their calibration and give increasingly
personalized advice.

**Owner:** khimdeeee@gmail.com (GitHub: `khimd25`). Non-technical; needs concrete,
step-by-step terminal instructions, not high-level pointers.

---

## 2. Repository

- **GitHub:** `khimd25/khim-react-router`
- **Working branch:** `claude/kalshi-trading-agent-5E6du` (all work lives here; not yet merged to main)
- **No PR has been opened** (owner has not requested one).

### Commit history (most recent last)
```
3239c48 Scaffold Kalshi trading consultant agent
dca21fa Add doctor command to verify setup and connectivity
a8b6d8f Add SessionStart hook for Claude Code on the web
2ac6daa Add pytest suite (57 tests) and ruff linter, wire into SessionStart hook
5f57f24 Add local setup guide (SETUP.md)
f19abf9 Support Python 3.9+ (revert 3.10/3.11-only idioms)
```

---

## 3. Architecture & file map

```
kalshi_agent/
  config.py              Settings dataclass, loaded from env vars (.env via python-dotenv)
  cli.py                 argparse CLI: chat | markets | journal | stats | doctor
  kalshi/
    auth.py              RSA-PSS (SHA-256) request signing for Kalshi API key auth
    client.py            KalshiClient REST wrapper (markets, orderbook, balance, positions, fills)
  analysis/
    stats.py             implied_probability, expected_value, edge, kelly_fraction, evaluate_trade
    calibration.py       brier_score, calibration_table, report
  journal/
    store.py             JournalStore (SQLite): add/resolve/list trades, performance_summary
  agent/
    prompts.py           BASE_SYSTEM prompt + build_system_prompt() that loads knowledge/*.md
    consultant.py        Consultant class; @beta_tool tool defs; Anthropic tool_runner loop

knowledge/
  strategies.md          Owner's personal trading rules / risk management (edit to grow the agent)
  market_notes.md        Owner's market observations (edit to grow the agent)

tests/                   pytest suite, 57 tests (stats, calibration, journal, auth, cli)
.claude/
  settings.json          Registers the SessionStart hook
  hooks/session-start.sh SessionStart hook (web only): venv + deps + ruff + pytest + doctor
SETUP.md                 Local setup guide for the owner's Mac
pyproject.toml           ruff + pytest config; requires-python >=3.9
requirements.txt         anthropic, requests, cryptography, python-dotenv, pytest, ruff
.env.example             Template for credentials
.gitignore               Ignores .env, *.pem, *.key, *.db, venv, caches
```

---

## 4. Key technical decisions & facts

### Kalshi API
- **Auth:** API-key RSA-PSS signatures. Message signed = `timestamp_ms + HTTP_METHOD + path`
  (path WITHOUT query string). Three headers per request: `KALSHI-ACCESS-KEY`,
  `KALSHI-ACCESS-TIMESTAMP` (unix ms), `KALSHI-ACCESS-SIGNATURE` (base64).
  PSS uses `MGF1(SHA256)` and `salt_length = DIGEST_LENGTH`.
- **Hosts:** production `https://api.elections.kalshi.com`; demo `https://demo-api.kalshi.co`.
  API prefix is `/trade-api/v2`. **An API key only works on the host it was created on.**
- **Contracts** trade in cents 1–99; a Yes contract pays 100¢ if the event happens.
  Implied probability = price/100.

### AI / Anthropic SDK
- Model default `claude-opus-4-8` (override via `KALSHI_AGENT_MODEL`).
- Uses `client.beta.messages.tool_runner()` for the automatic agentic loop.
- Tools are module-level `@beta_tool` functions; live `client`/`journal` are injected via a
  module-level `_CTX` dict (the SDK introspects bare functions, so they can't be bound methods).
- Adaptive thinking (`thinking={"type": "adaptive"}`), `effort: high`, system prompt is
  **prompt-cached** (`cache_control: ephemeral`) so multi-turn chat is cheap.

### Quant
- **Kelly** position sizing, half-Kelly by default. **Brier score** + equal-width calibration
  bins for scoring forecast accuracy.

### Python compatibility
- **Targets Python 3.9+.** The owner's Mac ships system Python 3.9. An earlier ruff
  auto-fix introduced `datetime.UTC` (3.11+) and `zip(strict=True)` (3.10+), which crashed
  on 3.9; both were reverted (commit `f19abf9`) and `requires-python`/ruff `target-version`
  were lowered to `py39`. **Do not reintroduce 3.10+ runtime idioms** unless the owner upgrades
  Python. Union type hints (`X | None`) are fine because every module has
  `from __future__ import annotations`.

---

## 5. Current state

- ✅ Full scaffold complete and committed.
- ✅ 57 pytest tests pass; ruff clean.
- ✅ `doctor` command verifies setup end-to-end (Anthropic key, Kalshi creds, key load,
  authenticated balance call, live market data).
- ✅ SessionStart hook works on Claude Code web (creates venv, installs deps, runs ruff +
  pytest + doctor). Guarded to only run when `CLAUDE_CODE_REMOTE=true`.
- 🟡 **Owner is mid-setup on their local Mac.** They cloned the repo, created a venv,
  and were running `doctor`. The 3.9 ImportError (now fixed) was the last blocker; next step
  for them is `git pull` then re-run `doctor`.

---

## 6. Open items / pending work

1. **SECURITY — rotate the Kalshi key.** During setup the owner pasted their **production**
   private key directly into chat, so it is exposed in the transcript. Key id
   `17f553e7-f497-41f3-95e6-8da38a51344b`. They were advised to delete it in the Kalshi
   dashboard and generate a new key pair. Account balance is ~$0.006, so practical risk is
   low, but this should still be done. The committed `.env.example` and `SETUP.md` reference
   the placeholder; the real `.env` and `kalshi_private_key.pem` are gitignored and exist only
   locally (and in the ephemeral web container).

2. **Owner must add `ANTHROPIC_API_KEY`** to their local `.env` to enable `chat`. Everything
   else works without it.

3. **No order placement / execution.** The client is read-only plus journaling — it never
   submits orders to Kalshi. If the owner asks to actually place trades, that is a deliberate,
   unbuilt next step (Kalshi `POST /portfolio/orders`) and should be gated carefully.

4. **Knowledge base is seed-only.** `knowledge/*.md` are templates; they get richer as the
   owner writes into them.

5. **Conversation memory is in-process only.** `Consultant._messages` holds history for the
   running session; nothing persists chat across runs except the SQLite journal.

---

## 7. How to run it

### Local (owner's Mac), one-time
```bash
cd ~/Documents
git clone https://github.com/khimd25/khim-react-router.git
cd khim-react-router
git checkout claude/kalshi-trading-agent-5E6du
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then edit: ANTHROPIC_API_KEY + Kalshi creds
# place the Kalshi private key file at ./kalshi_private_key.pem
```

### Every time after
```bash
cd ~/Documents/khim-react-router
source .venv/bin/activate
python -m kalshi_agent.cli doctor   # verify
python -m kalshi_agent.cli chat     # talk to the consultant
```

Other commands: `markets`, `journal list|add|resolve`, `stats`. See `SETUP.md` for full detail.

### Tests / lint
```bash
pytest tests/ -q
ruff check kalshi_agent/ tests/
```

---

## 8. Notes for the next agent

- **The owner is non-technical.** Give exact copy-paste terminal commands and say what they
  should see after each. Distinguish clearly between *their Mac's terminal* and any
  cloud/remote environment — this caused real confusion (they kept looking for project files
  in Finder that only existed in the remote container).
- **You cannot touch the owner's local machine.** If running in a remote/web Claude Code
  container, you can only edit files in that container and push to GitHub; the owner pulls.
- **Secrets never get committed** (`.env`, `*.pem` are gitignored). Don't try to "fill in"
  the owner's local `.env` from a remote session — it's a different machine.
- **Keep Python 3.9-compatible** until told otherwise (see §4).
- **Commit-message footer convention** is in use; match existing style. Don't open a PR unless
  explicitly asked.
