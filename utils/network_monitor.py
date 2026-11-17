"""
Network monitoring for UI tests – the pytest equivalent of keeping the browser's Network tab open.

Attach a `NetworkMonitor` to a page and it records every XHR/fetch call (method, URL, status,
request body and, for write calls, the response body). Tests then assert on what actually went
over the wire, e.g. "no create request succeeded" or "the server never answered with a 5xx".
"""

import re
from dataclasses import dataclass, field
from urllib.parse import urlparse

from playwright.sync_api import Page, Request, Response

WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

# Signs that a server error page / debug output is leaking implementation details
LEAK_PATTERN = re.compile(
    r"stack ?trace|traceback|sqlstate|syntax error|vendor[/\\]|\.php\b|\"exception\"|\"trace\"|"
    r"illuminate\\|laravel|mysql|psql|select .* from |/var/www|c:\\\\",
    re.I,
)


@dataclass
class Call:
    method: str
    url: str
    status: int
    request_body: str | None = None
    response_body: str | None = None

    @property
    def path(self) -> str:
        return re.sub(r"^https?://[^/]+", "", self.url)

    def __str__(self) -> str:
        return f"{self.method} {self.path} -> {self.status}"


@dataclass
class NetworkMonitor:
    page: Page
    hosts: tuple[str, ...] = ("misbackend.com",)  # only the app's own API traffic (not Google Maps etc.)
    calls: list[Call] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.page.on("response", self._on_response)
        self.page.on("requestfailed", self._on_failed)

    # ── recording ────────────────────────────────────────────────────────────

    def _is_app_host(self, url: str) -> bool:
        host = urlparse(url).hostname or ""
        return any(host == h or host.endswith("." + h) for h in self.hosts)

    def _on_response(self, response: Response) -> None:
        request = response.request
        if request.resource_type not in ("xhr", "fetch") or not self._is_app_host(response.url):
            return
        body = None
        if request.method in WRITE_METHODS:
            try:
                body = response.text()
            except Exception:  # body can be unavailable (redirects, aborted)
                body = None
        self.calls.append(
            Call(request.method, response.url, response.status, request.post_data, body)
        )

    def _on_failed(self, request: Request) -> None:
        if request.resource_type in ("xhr", "fetch") and self._is_app_host(request.url):
            self.failures.append(f"{request.method} {request.url} ({request.failure})")

    # ── queries ──────────────────────────────────────────────────────────────

    def clear(self) -> None:
        self.calls.clear()
        self.failures.clear()

    def writes(self) -> list[Call]:
        """Create/update/delete calls (POST, PUT, PATCH, DELETE)."""
        return [c for c in self.calls if c.method in WRITE_METHODS]

    def successful_writes(self) -> list[Call]:
        return [c for c in self.writes() if 200 <= c.status < 300]

    def server_errors(self) -> list[Call]:
        return [c for c in self.calls if c.status >= 500]

    def leaks(self) -> list[Call]:
        """Write responses whose body looks like a stack trace / SQL / file-path leak."""
        return [c for c in self.writes() if c.response_body and LEAK_PATTERN.search(c.response_body)]

    def summary(self) -> str:
        writes = ", ".join(str(c) for c in self.writes()) or "no write request was sent"
        return f"{writes}; failures: {self.failures or 'none'}"
