"""Command-line interface for the Kalshi trading consultant.

Usage:
    python -m kalshi_agent.cli chat                  # interactive consultant
    python -m kalshi_agent.cli markets [--status open --limit 20]
    python -m kalshi_agent.cli journal list [--status open]
    python -m kalshi_agent.cli journal resolve <id> --outcome 1
    python -m kalshi_agent.cli stats                 # your calibration + P&L
"""

from __future__ import annotations

import argparse
import sys

from .analysis import calibration
from .config import load_settings
from .journal import JournalStore
from .kalshi import KalshiClient


def _make_client(settings) -> KalshiClient:
    return KalshiClient(
        api_base=settings.kalshi_api_base,
        api_prefix=settings.kalshi_api_prefix,
        key_id=settings.kalshi_key_id,
        private_key_path=settings.kalshi_private_key_path,
    )


def cmd_chat(settings, args) -> int:
    if not settings.anthropic_api_key:
        print("ERROR: ANTHROPIC_API_KEY is not set. See .env.example.", file=sys.stderr)
        return 1
    if not settings.kalshi_configured:
        print("WARNING: Kalshi credentials not set — live data tools will fail.\n", file=sys.stderr)

    # Imported here so `markets`/`journal`/`stats` work without the anthropic SDK.
    from .agent import Consultant

    client = _make_client(settings)
    journal = JournalStore(settings.journal_db_path)
    consultant = Consultant(
        client=client,
        journal=journal,
        knowledge_dir=settings.knowledge_dir,
        model=settings.model,
        anthropic_api_key=settings.anthropic_api_key,
    )

    print(f"Kalshi consultant ready ({settings.model}). Type 'exit' to quit.\n")
    try:
        while True:
            try:
                user = input("you> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if user.lower() in {"exit", "quit"}:
                break
            if not user:
                continue
            print()
            answer = consultant.ask(user)
            print(f"agent> {answer}\n")
    finally:
        journal.close()
    return 0


def cmd_markets(settings, args) -> int:
    client = _make_client(settings)
    data = client.get_markets(status=args.status, limit=args.limit)
    markets = data.get("markets", [])
    if not markets:
        print("No markets returned.")
        return 0
    for m in markets:
        print(f"{m.get('ticker'):<24} yes_ask={m.get('yes_ask')!s:>4}c "
              f"vol={m.get('volume')!s:>7}  {m.get('title')}")
    return 0


def cmd_journal(settings, args) -> int:
    journal = JournalStore(settings.journal_db_path)
    try:
        if args.journal_cmd == "list":
            status = None if args.status == "all" else args.status
            trades = journal.list_trades(status=status)
            if not trades:
                print("No trades logged yet.")
                return 0
            for t in trades:
                pnl = f"{t.pnl_cents/100:+.2f}$" if t.pnl_cents is not None else "-"
                pred = f"{t.predicted_prob:.0%}" if t.predicted_prob is not None else "-"
                print(f"#{t.id:<4} {t.status:<8} {t.market_ticker:<22} "
                      f"{t.side:<3} @ {t.entry_price:>3.0f}c x{t.contracts:<4} "
                      f"pred={pred:<5} pnl={pnl}")
        elif args.journal_cmd == "add":
            tid = journal.add_trade(
                args.ticker, args.side, args.price, args.contracts,
                args.prob, args.rationale,
            )
            print(f"Logged trade #{tid}.")
        elif args.journal_cmd == "resolve":
            t = journal.resolve_trade(args.id, args.outcome, args.exit_price)
            if t is None:
                print(f"No trade #{args.id}.")
                return 1
            print(f"Resolved trade #{t.id}: outcome={t.outcome} pnl={t.pnl_cents/100:+.2f}$")
    finally:
        journal.close()
    return 0


def cmd_doctor(settings, args) -> int:
    """Run setup/connectivity checks so you can verify a machine in one command."""
    ok = "\033[32m✓\033[0m"
    warn = "\033[33m!\033[0m"
    fail = "\033[31m✗\033[0m"
    hard_failures = 0

    print("Kalshi consultant — setup check\n")
    print(f"  config: model={settings.model}  host={settings.kalshi_api_base}")
    print(f"          journal={settings.journal_db_path}")
    print(f"          knowledge={settings.knowledge_dir}\n")

    # 1. Anthropic key (needed only for `chat`).
    if settings.anthropic_api_key:
        print(f"  {ok} ANTHROPIC_API_KEY is set (needed for `chat`)")
    else:
        print(f"  {warn} ANTHROPIC_API_KEY not set — `chat` won't work, everything else will")

    # 2. Kalshi credentials present.
    if not settings.kalshi_configured:
        print(f"  {fail} Kalshi credentials missing — set KALSHI_KEY_ID and KALSHI_PRIVATE_KEY_PATH")
        print("\nSee .env.example. Fix the above and re-run `doctor`.")
        return 1
    print(f"  {ok} Kalshi credentials present (key id + private key path)")

    # 3. Private key loads.
    try:
        from .kalshi.auth import load_private_key
        pk = load_private_key(settings.kalshi_private_key_path)
        print(f"  {ok} private key loads ({pk.key_size}-bit RSA)")
    except Exception as e:
        print(f"  {fail} private key failed to load: {type(e).__name__}: {str(e)[:120]}")
        return 1

    client = _make_client(settings)

    # 4. Authenticated request (balance).
    try:
        bal = client.get_balance()
        dollars = bal.get("balance_dollars", bal.get("balance"))
        print(f"  {ok} Kalshi auth works — account balance: ${dollars}")
    except Exception as e:
        hard_failures += 1
        msg = getattr(e, "body", str(e))
        print(f"  {fail} Kalshi auth failed: {str(msg)[:160]}")
        print("      (is KALSHI_API_BASE right? key works only on the host it was created on)")

    # 5. Live market data.
    try:
        markets = client.get_markets(status="open", limit=1).get("markets", [])
        if markets:
            print(f"  {ok} live market data — sample: {markets[0].get('ticker')}")
        else:
            print(f"  {warn} market data request worked but returned no open markets")
    except Exception as e:
        hard_failures += 1
        print(f"  {fail} market data request failed: {str(getattr(e, 'body', e))[:160]}")

    print()
    if hard_failures:
        print(f"{fail} {hard_failures} check(s) failed — see above.")
        return 1
    print(f"{ok} All systems go." + ("" if settings.anthropic_api_key
                                      else " (add ANTHROPIC_API_KEY to enable `chat`)"))
    return 0


def cmd_stats(settings, args) -> int:
    journal = JournalStore(settings.journal_db_path)
    try:
        perf = journal.performance_summary()
        print("Performance")
        print(f"  Resolved trades: {perf['resolved_trades']}")
        print(f"  Open trades:     {perf['open_trades']}")
        print(f"  Total P&L:       {perf['total_pnl_dollars']:+.2f}$")
        if perf["win_rate"] is not None:
            print(f"  Win rate:        {perf['win_rate']:.1%}")
        print()
        preds, outs = journal.resolved_predictions()
        print(calibration.report(preds, outs))
    finally:
        journal.close()
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="kalshi_agent", description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("chat", help="Interactive consultant")
    sub.add_parser("doctor", help="Verify setup: credentials, auth, live data")

    pm = sub.add_parser("markets", help="List live markets")
    pm.add_argument("--status", default="open")
    pm.add_argument("--limit", type=int, default=20)

    pj = sub.add_parser("journal", help="Manage the trade journal")
    jsub = pj.add_subparsers(dest="journal_cmd", required=True)
    jl = jsub.add_parser("list")
    jl.add_argument("--status", default="all", choices=["all", "open", "resolved"])
    ja = jsub.add_parser("add")
    ja.add_argument("ticker")
    ja.add_argument("side", choices=["yes", "no"])
    ja.add_argument("price", type=float, help="entry price in cents")
    ja.add_argument("contracts", type=int)
    ja.add_argument("--prob", type=float, help="your probability (0-1) this side pays out")
    ja.add_argument("--rationale", default="")
    jr = jsub.add_parser("resolve")
    jr.add_argument("id", type=int)
    jr.add_argument("--outcome", type=int, required=True, choices=[0, 1],
                    help="1 if your side paid out, else 0")
    jr.add_argument("--exit-price", type=float, default=None,
                    help="cents, if you closed before settlement")

    sub.add_parser("stats", help="Show your calibration and P&L")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    settings = load_settings()

    if args.command == "chat":
        return cmd_chat(settings, args)
    if args.command == "doctor":
        return cmd_doctor(settings, args)
    if args.command == "markets":
        return cmd_markets(settings, args)
    if args.command == "journal":
        return cmd_journal(settings, args)
    if args.command == "stats":
        return cmd_stats(settings, args)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
