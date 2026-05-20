import os
import pytest
import requests
from playwright.sync_api import Page, APIRequestContext
from dotenv import load_dotenv

load_dotenv(".env.test")
HOSTING_BASE   = "http://127.0.0.1:5050"      # Firebase Hosting emulator (SPA)
AUTH_EMULATOR   = "http://127.0.0.1:9099"      # Firebase Auth emulator
API_BASE        = "http://127.0.0.1:8000"      # FastAPI backend
TEST_EMAIL      = os.getenv("TEST_EMAIL", "test@vrptw.local")
TEST_PASSWORD   = os.getenv("TEST_PASSWORD", "testpass123")


@pytest.fixture(scope="session", autouse=True)
def seed_emulator_user():
    """Create the test user in the Firebase Auth Emulator before any tests run."""
    url = f"{AUTH_EMULATOR}/identitytoolkit.googleapis.com/v1/accounts:signUp?key=fake-api-key"
    payload = {
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD,
        "returnSecureToken": True,
    }
    try:
        resp = requests.post(url, json=payload, timeout=5)
        if resp.status_code == 200:
            print(f"\n[Emulator] Seeded user: {TEST_EMAIL}")
        elif resp.status_code == 400 and "EMAIL_EXISTS" in resp.text:
            print(f"\n[Emulator] User already exists: {TEST_EMAIL}")
        else:
            print(f"\n[Emulator] Seed response: {resp.status_code} {resp.text}")
    except requests.ConnectionError:
        pytest.fail(
            "Firebase Auth Emulator is not running on port 9099.\n"
            "Start it with: make emulators"
        )
    yield


@pytest.fixture
def authed_page(page: Page):
    """Fixture that logs in via the UI before yielding the page."""
    page.on("console", lambda msg: print(f"\n[Console]: {msg.text}"))
    page.on("pageerror", lambda err: print(f"\n[FATAL JS ERROR]: {err}"))

    page.goto(f"{HOSTING_BASE}/app.html")
    page.wait_for_load_state("networkidle")

    if not (TEST_EMAIL and TEST_PASSWORD):
        pytest.fail("TEST_EMAIL or TEST_PASSWORD not found in .env.test")

    # Dismiss the help modal if it appears
    try:
        page.wait_for_selector("#help-modal-close", state="visible", timeout=3000)
        page.click("#help-modal-close")
    except Exception:
        pass

    page.wait_for_timeout(500)

    # Fill login form and submit
    page.fill("#login-email", TEST_EMAIL)
    page.fill("#login-password", TEST_PASSWORD)
    page.click("#btn-login")

    # Wait for auth screen to hide (login success)
    try:
        page.wait_for_selector("#auth-screen", state="hidden", timeout=15000)
    except Exception as e:
        page.screenshot(path="tests/e2e/screenshots/DEBUG_auth_stuck.png", full_page=True)
        visible_text = page.locator("#auth-screen").inner_text(timeout=2000)
        print(f"\n[UI VISIBLE TEXT]:\n{visible_text}")
        raise e

    page.wait_for_selector("#app-shell", state="visible", timeout=15000)
    return page


@pytest.fixture
def authed_api(authed_page: Page, playwright) -> APIRequestContext:
    """Extract the Firebase JWT from the logged-in page and create an
    authenticated API request context for backend calls."""
    token = authed_page.evaluate("() => localStorage.getItem('vrptw_token')")
    assert token, "No auth token found in localStorage after login"

    api = playwright.request.new_context(
        base_url=API_BASE,
        extra_http_headers={"Authorization": f"Bearer {token}"},
    )
    yield api
    api.dispose()