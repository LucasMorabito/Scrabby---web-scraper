import os
import random
import time
from collections.abc import Mapping
from typing import Any

from curl_cffi import requests as cffi_requests


DEFAULT_IMPERSONATE = os.getenv("SCRABBY_TLS_IMPERSONATE", "chrome146")
DEFAULT_TIMEOUT = float(os.getenv("SCRABBY_HTTP_TIMEOUT", "15"))
DEFAULT_MAX_ATTEMPTS = int(os.getenv("SCRABBY_HTTP_MAX_ATTEMPTS", "3"))
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

BASE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/146.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "es-AR,es;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Sec-Ch-Ua": '"Chromium";v="146", "Google Chrome";v="146", "Not_A Brand";v="99"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}


def create_stealth_session(
    *,
    impersonate: str = DEFAULT_IMPERSONATE,
    headers: Mapping[str, str] | None = None,
) -> cffi_requests.Session:
    session = cffi_requests.Session(impersonate=impersonate)
    session.headers.update(BASE_HEADERS)
    if headers:
        session.headers.update(dict(headers))
    return session


class StealthHttpClient:
    def __init__(
        self,
        *,
        impersonate: str = DEFAULT_IMPERSONATE,
        headers: Mapping[str, str] | None = None,
        timeout: float = DEFAULT_TIMEOUT,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
        backoff_base: float = 0.75,
        backoff_max: float = 6.0,
    ) -> None:
        self.session = create_stealth_session(impersonate=impersonate, headers=headers)
        self.impersonate = impersonate
        self.timeout = timeout
        self.max_attempts = max(1, max_attempts)
        self.backoff_base = backoff_base
        self.backoff_max = backoff_max

    def get(self, url: str, **kwargs: Any) -> cffi_requests.Response:
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs: Any) -> cffi_requests.Response:
        return self.request("POST", url, **kwargs)

    def request(self, method: str, url: str, **kwargs: Any) -> cffi_requests.Response:
        kwargs.setdefault("timeout", self.timeout)
        kwargs.setdefault("impersonate", self.impersonate)

        last_error: Exception | None = None
        for attempt in range(1, self.max_attempts + 1):
            try:
                response = self.session.request(method, url, **kwargs)
                if response.status_code not in RETRYABLE_STATUS_CODES or attempt == self.max_attempts:
                    return response
            except cffi_requests.RequestsError as exc:
                last_error = exc
                if attempt == self.max_attempts:
                    raise

            self._sleep_before_retry(attempt)

        if last_error:
            raise last_error

        raise RuntimeError("HTTP request failed without a response")

    def _sleep_before_retry(self, attempt: int) -> None:
        delay = min(self.backoff_max, self.backoff_base * (2 ** (attempt - 1)))
        time.sleep(delay + random.uniform(0, delay / 2))


def create_stealth_http_client(**kwargs: Any) -> StealthHttpClient:
    return StealthHttpClient(**kwargs)
