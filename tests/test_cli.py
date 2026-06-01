from __future__ import annotations

import pytest

from kalshi_agent.cli import build_parser


class TestBuildParser:
    def test_chat_command(self):
        args = build_parser().parse_args(["chat"])
        assert args.command == "chat"

    def test_doctor_command(self):
        args = build_parser().parse_args(["doctor"])
        assert args.command == "doctor"

    def test_markets_defaults(self):
        args = build_parser().parse_args(["markets"])
        assert args.command == "markets"
        assert args.status == "open"
        assert args.limit == 20

    def test_markets_custom(self):
        args = build_parser().parse_args(["markets", "--status", "closed", "--limit", "5"])
        assert args.status == "closed"
        assert args.limit == 5

    def test_journal_list(self):
        args = build_parser().parse_args(["journal", "list"])
        assert args.command == "journal"
        assert args.journal_cmd == "list"
        assert args.status == "all"

    def test_journal_add(self):
        args = build_parser().parse_args(
            ["journal", "add", "TICKER", "yes", "55", "10", "--prob", "0.7"]
        )
        assert args.ticker == "TICKER"
        assert args.side == "yes"
        assert args.price == 55.0
        assert args.contracts == 10
        assert args.prob == 0.7

    def test_journal_resolve(self):
        args = build_parser().parse_args(
            ["journal", "resolve", "1", "--outcome", "1", "--exit-price", "80"]
        )
        assert args.id == 1
        assert args.outcome == 1
        assert args.exit_price == 80.0

    def test_stats_command(self):
        args = build_parser().parse_args(["stats"])
        assert args.command == "stats"

    def test_missing_command_exits(self):
        with pytest.raises(SystemExit):
            build_parser().parse_args([])
