"""A thin, typed-ish REST client for the Kalshi Trade API v2.

Public market-data endpoints (markets, events, orderbook) don't strictly need
auth, but portfolio endpoints (balance, positions, orders) do. We sign every
request when credentials are present so both work uniformly.

Docs: https://docs.kalshi.com  (fetch /llms.txt for the full endpoint index)
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

import requests

from .auth import auth_headers, load_private_key


class KalshiClient:
    def __init__(
        self,
        api_base: str,
        api_prefix: str,
        key_id: str | None = None,
        private_key_path: str | None = None,
        timeout: float = 15.0,
    ) -> None:
        self.api_base = api_base.rstrip("/")
        self.api_prefix = api_prefix
        self.key_id = key_id
        self.timeout = timeout
        self._private_key = load_private_key(private_key_path) if private_key_path else None
        self._session = requests.Session()

    # -- low-level ---------------------------------------------------------

    def _request(self, method: str, endpoint: str, params: dict | None = None,
                 json: dict | None = None) -> dict[str, Any]:
        # The path used for signing must NOT include the query string.
        path = f"{self.api_prefix}{endpoint}"
        url = f"{self.api_base}{path}"

        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self.key_id and self._private_key:
            headers.update(auth_headers(self._private_key, self.key_id, method, path))

        resp = self._session.request(
            method,
            url,
            params=params,
            json=json,
            headers=headers,
            timeout=self.timeout,
        )
        if resp.status_code >= 400:
            raise KalshiAPIError(resp.status_code, resp.text, url)
        return resp.json() if resp.content else {}

    # -- market data -------------------------------------------------------

    def get_markets(self, limit: int = 50, status: str | None = None,
                    event_ticker: str | None = None, series_ticker: str | None = None,
                    cursor: str | None = None) -> dict[str, Any]:
        """List markets. status is one of: unopened, open, closed, settled."""
        params = {"limit": limit}
        if status:
            params["status"] = status
        if event_ticker:
            params["event_ticker"] = event_ticker
        if series_ticker:
            params["series_ticker"] = series_ticker
        if cursor:
            params["cursor"] = cursor
        return self._request("GET", "/markets", params=params)

    def get_market(self, ticker: str) -> dict[str, Any]:
        return self._request("GET", f"/markets/{ticker}")

    def get_orderbook(self, ticker: str, depth: int = 10) -> dict[str, Any]:
        return self._request("GET", f"/markets/{ticker}/orderbook", params={"depth": depth})

    def get_event(self, event_ticker: str) -> dict[str, Any]:
        return self._request("GET", f"/events/{event_ticker}")

    def get_events(self, limit: int = 50, status: str | None = None,
                   cursor: str | None = None) -> dict[str, Any]:
        params: dict[str, Any] = {"limit": limit}
        if status:
            params["status"] = status
        if cursor:
            params["cursor"] = cursor
        return self._request("GET", "/events", params=params)

    # -- portfolio (requires auth) ----------------------------------------

    def get_balance(self) -> dict[str, Any]:
        return self._request("GET", "/portfolio/balance")

    def get_positions(self, limit: int = 100) -> dict[str, Any]:
        return self._request("GET", "/portfolio/positions", params={"limit": limit})

    def get_fills(self, limit: int = 100) -> dict[str, Any]:
        return self._request("GET", "/portfolio/fills", params={"limit": limit})


class KalshiAPIError(RuntimeError):
    def __init__(self, status_code: int, body: str, url: str) -> None:
        self.status_code = status_code
        self.body = body
        self.url = url
        super().__init__(f"Kalshi API {status_code} for {url}: {body[:300]}")
