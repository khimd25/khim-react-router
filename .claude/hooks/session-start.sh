#!/bin/bash
# SessionStart hook for Claude Code on the web.
# Installs Python dependencies into an isolated venv (robust against broken
# system packages) and runs the `doctor` check to surface setup status.
set -euo pipefail

# Only run in the remote (web) environment; locally you manage your own env.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "$CLAUDE_PROJECT_DIR"

VENV="$CLAUDE_PROJECT_DIR/.venv"

# Create the venv once; reuse it on subsequent sessions (container state is
# cached after the hook completes, so this stays fast).
if [ ! -d "$VENV" ]; then
  python3 -m venv "$VENV"
fi

"$VENV/bin/pip" install -q --upgrade pip
"$VENV/bin/pip" install -q -r requirements.txt

# Persist for the session: use the venv's tools and make the package importable
# from anywhere (so `python -m kalshi_agent.cli ...` just works).
echo "export PATH=\"$VENV/bin:\$PATH\"" >> "$CLAUDE_ENV_FILE"
echo "export PYTHONPATH=\"$CLAUDE_PROJECT_DIR\"" >> "$CLAUDE_ENV_FILE"

# Surface setup status. Credentials live in a gitignored .env (absent in fresh
# web sessions) or in the environment's configured secrets, so `doctor` flags
# whatever still needs configuring. Non-fatal — never block session startup.
"$VENV/bin/python" -m kalshi_agent.cli doctor || true
