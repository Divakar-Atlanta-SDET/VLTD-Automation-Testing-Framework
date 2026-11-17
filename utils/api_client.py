"""
Minimal API client for the VLTD back-end.

It lets tests send requests the UI would never produce (over-long values, wrong types, missing
tokens, another user's token) to verify what the SERVER enforces, independent of the front-end.
"""

import time

from playwright.sync_api import APIRequestContext, APIResponse, Page

API_PREFIX = "/api/transport-commissioner"


class ApiClient:
    """Bearer-token client on top of a Playwright APIRequestContext.

    `request(..., token="session")` uses this client's own token, `token=None` sends none, and any other
    string is used as the bearer token (e.g. a different user's).
    """

    def __init__(self, request: APIRequestContext, origin: str, token: str | None = None) -> None:
        self.api = request
        self.origin = origin.rstrip("/")
        self.token = token

    @classmethod
    def login(cls, request: APIRequestContext, origin: str, email: str, password: str) -> "ApiClient":
        client = cls(request, origin)
        for attempt in range(4):  # parallel workers can briefly trip rate limiting / transient errors
            response = client.post("/api/auth/login", json={"email": email, "password": password}, token=None)
            if response.ok or response.status not in (429, 500, 502, 503, 504):
                break
            time.sleep(2 * (attempt + 1))
        assert response.ok, f"Login failed for {email}: {response.status} {response.text()[:200]}"
        client.token = response.json()["data"]["access_token"]
        return client

    def request(
        self,
        method: str,
        path: str,
        *,
        json: dict | list | None = None,
        multipart: dict | None = None,
        token: str | None = "session",
        origin: str | None = None,
    ) -> APIResponse:
        headers = {"Accept": "application/json"}
        bearer = self.token if token == "session" else token
        if bearer:
            headers["Authorization"] = f"Bearer {bearer}"
        return self.api.fetch(
            (origin or self.origin) + path,
            method=method,
            headers=headers,
            data=json,
            multipart=multipart,
            max_redirects=0,
        )

    def get(self, path: str, **kwargs) -> APIResponse:
        return self.request("GET", path, **kwargs)

    def post(self, path: str, json: dict | list | None = None, **kwargs) -> APIResponse:
        return self.request("POST", path, json=json, **kwargs)

    def put(self, path: str, json: dict | list | None = None, **kwargs) -> APIResponse:
        return self.request("PUT", path, json=json, **kwargs)

    def delete(self, path: str, **kwargs) -> APIResponse:
        return self.request("DELETE", path, **kwargs)

    def patch(self, path: str, json: dict | list | None = None, **kwargs) -> APIResponse:
        return self.request("PATCH", path, json=json, **kwargs)

    # ── look-ups used to build a valid request body ──────────────────────────

    def list_items(self, path: str) -> list[dict]:
        """Items of a list endpoint ({"data": [...]} or paginated {"data": {"data": [...]}})."""
        data = self.get(path).json()["data"]
        return data.get("data", []) if isinstance(data, dict) else data

    def all_items(self, path: str) -> list[dict]:
        """Every item of a paginated list endpoint (the API serves at most 100 per page)."""
        items, page = [], 1
        while True:
            body = self.get(f"{path}?per_page=100&page={page}").json()
            items += body["data"]
            paging = body.get("pagination") or (body.get("meta") or {}).get("pagination") or {}  # either envelope
            if page >= paging.get("last_page", 1):
                return items
            page += 1

    def first_id(self, path: str) -> int:
        return self.list_items(path)[0]["id"]


class AdminApi(ApiClient):
    """The admin that is logged in on `page` (bearer token read from the page's localStorage)."""

    def __init__(self, page: Page) -> None:
        origin = "/".join(page.url.split("/")[:3])
        super().__init__(page.request, origin, page.evaluate("() => localStorage.getItem('access_token')"))
        self.page = page
