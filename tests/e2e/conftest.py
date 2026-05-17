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
    # 1. Catch ALL console logs to see what your JS catch block is swallowing
    page.on("console", lambda msg: print(f"\n[Console]: {msg.text}"))
    
    # 2. THE UNFILTERED X-RAY: Print every single network response
    page.on("response", lambda resp: print(f"\n[Network IN]: {resp.status} {resp.url}"))

    page.goto(f"{BASE}/app.html")
    page.wait_for_load_state("networkidle")

    if not (TEST_EMAIL and TEST_PASSWORD):
        pytest.fail("TEST_EMAIL or TEST_PASSWORD not found in .env.test")

    # Wait for the button to unlock naturally
    page.wait_for_selector("#btn-login:not([disabled])", timeout=15000)

    # Type credentials
    page.fill("#login-email", TEST_EMAIL)
    page.fill("#login-password", TEST_PASSWORD)
    
    # Force the click via JavaScript to guarantee it triggers the event listener
    page.evaluate("document.getElementById('btn-login').click()")

    # Dismiss the Guide (if it pops up)
    try:
        page.wait_for_selector("#help-modal-close", state="visible", timeout=3000)
        page.click("#help-modal-close")
    except Exception:
        pass

    # Wait for the screen to hide
    try:
        page.wait_for_selector("#auth-screen", state="hidden", timeout=10000)
    except Exception as e:
        page.screenshot(path="tests/e2e/screenshots/DEBUG_auth_stuck.png", full_page=True)
        raise e
        
    page.wait_for_load_state("networkidle")
    return page