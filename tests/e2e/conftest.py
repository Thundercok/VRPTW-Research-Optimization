import os
import pytest
from playwright.sync_api import Page
from dotenv import load_dotenv

# Load the test credentials
load_dotenv(".env.test")
BASE = "http://127.0.0.1:8000"
TEST_EMAIL = os.getenv("TEST_EMAIL")
TEST_PASSWORD = os.getenv("TEST_PASSWORD")

@pytest.fixture
def authed_page(page: Page):
    """Fixture that logs in via the UI before yielding the page."""
    page.on("console", lambda msg: print(f"\n[Console]: {msg.text}"))
    page.on("response", lambda resp: print(f"\n[Network IN]: {resp.status} {resp.url}"))
    page.on("pageerror", lambda err: print(f"\n[FATAL JS ERROR]: {err}"))

    page.goto(f"{BASE}/app.html")
    page.wait_for_load_state("networkidle")

    if not (TEST_EMAIL and TEST_PASSWORD):
        pytest.fail("TEST_EMAIL or TEST_PASSWORD not found in .env.test")

    # THE FIX: Dismiss the help modal BEFORE trying to interact with the login form
    try:
        page.wait_for_selector("#help-modal-close", state="visible", timeout=3000)
        page.click("#help-modal-close")
        print("\n[Test] Dismissed the help modal.")
    except Exception:
        pass

    # Small pause to let the modal fade out and the JS to settle
    page.wait_for_timeout(1000)

    # Now that the screen is clear, type and click
    page.fill("#login-email", TEST_EMAIL)
    page.fill("#login-password", TEST_PASSWORD)
    page.click("#btn-login")

    # Wait for the screen to hide
    try:
        page.wait_for_selector("#auth-screen", state="hidden", timeout=10000)
    except Exception as e:
        page.screenshot(path="tests/e2e/screenshots/DEBUG_auth_stuck.png", full_page=True)
        # Scrape the screen for the UI Error Catcher we just built
        visible_text = page.locator(".auth-screen").inner_text(timeout=1000)
        print(f"\n[UI VISIBLE TEXT]:\n{visible_text}")
        raise e
        
    page.wait_for_load_state("networkidle")
    return page