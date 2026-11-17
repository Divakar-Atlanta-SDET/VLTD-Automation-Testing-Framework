"""
Profile, Change Password and Logout API, as the OEM panel uses it.

  GET   /api/auth/me                     the signed-in user (id, name, email, role)
  GET   /api/users/{id}                  a user's profile (name, email, contact_no, address, city, state) - the Profile page
  PUT   /api/users/{id}                  Edit Details AND the Change Password tab both call this: {name, email, contact_no} and,
                                          for a password change, additionally {current_password, password, password_confirmation}
  POST  /api/auth/change-password        the FORCED first-login page only: {current_password, new_password, new_password_confirmation}
  POST  /api/auth/logout                 ends the current access token; bearer token required
  POST  /api/auth/refresh                {refresh_token} -> a new access token (see BUG below: works after logout too)

Two different endpoints with two different field-name conventions do the same thing (forced change vs the Profile tab); see
bug_report.md observations for this module.
"""

from playwright.sync_api import APIRequestContext, Page

from utils import data_generator as data
from utils.api_client import ApiClient
from utils.oem_panel_api import create_oem_account

ME = "/api/auth/me"
USERS = "/api/users"
FORCE_CHANGE_PASSWORD = "/api/auth/change-password"
LOGOUT = "/api/auth/logout"
REFRESH = "/api/auth/refresh"


def me(client: ApiClient) -> dict:
    return client.get(ME).json()["data"]


def profile(client: ApiClient, user_id: str) -> dict:
    return client.get(f"{USERS}/{user_id}").json()["data"]


def update_profile(client: ApiClient, user_id: str, *, name: str, email: str, contact_no: str, **extra):
    """Edit Details, and (with `current_password` / `password` / `password_confirmation` in `extra`) the Change Password tab:
    both send the same PUT request."""
    return client.put(f"{USERS}/{user_id}", json={"name": name, "email": email, "contact_no": contact_no, **extra})


def change_password_tab(client: ApiClient, user: dict, current_password: str, new_password: str, confirmation: str | None = None):
    """The Profile > Change Password tab's request: the current name/email/contact_no are resent unchanged."""
    return update_profile(
        client, user["id"], name=user["name"], email=user["email"], contact_no=user.get("contact_no", ""),
        current_password=current_password, password=new_password, password_confirmation=new_password if confirmation is None else confirmation,
    )


def forced_change_password(client: ApiClient, current_password: str, new_password: str, confirmation: str | None = None):
    """The forced '/auth/change-password' page's request (a brand-new account's first login, or one whose password is 90+ days old)."""
    return client.post(FORCE_CHANGE_PASSWORD, json={
        "current_password": current_password, "new_password": new_password,
        "new_password_confirmation": new_password if confirmation is None else confirmation,
    })


def logout(client: ApiClient):
    return client.post(LOGOUT, json={})


def refresh(client: ApiClient, refresh_token: str):
    return client.post(REFRESH, json={"refresh_token": refresh_token})


def login_tokens(request: APIRequestContext, origin: str, email: str, password: str) -> dict:
    """The raw login response's `data` (access_token, refresh_token, user, ...), without building an ApiClient."""
    response = request.fetch(f"{origin.rstrip('/')}/api/auth/login", method="POST", headers={"Accept": "application/json"}, data={"email": email, "password": password})
    assert response.ok, f"login failed: {response.status} {response.text()[:200]}"
    return response.json()["data"]


def page_tokens(page: Page) -> dict:
    """The access_token / refresh_token a signed-in browser tab currently holds (read from its own localStorage)."""
    return page.evaluate("() => ({access: localStorage.getItem('access_token'), refresh: localStorage.getItem('refresh_token')})")


def settled_oem_account(admin: ApiClient, request: APIRequestContext, origin: str) -> dict:
    """A brand-new, throw-away OEM account that has already completed its forced first-login password change (through the API, so it
    is fast and does not depend on the UI). Returns {'id', 'email', 'password'} with the FINAL password. Never printed or logged."""
    account = create_oem_account(admin)
    temp_client = ApiClient.login(request, origin, account["email"], account["password"])
    settled_password = data.PASSWORD + "9"  # still meets the policy (10+, upper, lower, number); different from the temporary one
    response = forced_change_password(temp_client, account["password"], settled_password)
    assert response.status == 200, f"could not settle the throw-away account's password: {response.status} {response.text()[:200]}"
    return {**account, "password": settled_password}
