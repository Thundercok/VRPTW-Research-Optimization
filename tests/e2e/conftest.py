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
    # Listen to the browser's console so we can see real Firebase errors if they happen
    page.on("console", lambda msg: print(f"\n[Browser Console]: {msg.text}"))

    page.goto(f"{BASE}/app.html")
    page.wait_for_load_state("networkidle")

    if not (TEST_EMAIL and TEST_PASSWORD):
        pytest.fail("TEST_EMAIL or TEST_PASSWORD not found in .env.test")

    # Force-unlock inputs (Frontend JS might lock them while Firebase initializes)
    page.evaluate("document.getElementById('login-email').disabled = false")
    page.evaluate("document.getElementById('login-password').disabled = false")
    page.evaluate("document.getElementById('btn-login').disabled = false")

 # Type credentials and click login
    page.fill("#login-email", TEST_EMAIL, force=True)
    page.fill("#login-password", TEST_PASSWORD, force=True)
    page.click("#btn-login", force=True)

    # Dismiss the "How to Use" Guide Modal
    try:
        page.wait_for_selector("#help-modal-close", state="visible", timeout=5000)
        page.click("#help-modal-close", force=True)
        print("\n[Test] Dismissed the 'How to Use' guide.")
    except Exception:
        pass

    # Wait for the REAL Firebase auth to resolve and hide the screen
    try:
        page.wait_for_selector("#auth-screen", state="hidden", timeout=10000)
    except Exception as e:
        # THE FIX: Snap a screenshot of the exact failure state
        page.screenshot(path="tests/e2e/screenshots/DEBUG_auth_stuck.png", full_page=True)
        print("\n[FATAL] Auth screen did not hide. Screenshot saved to tests/e2e/screenshots/DEBUG_auth_stuck.png")
        raise e
        
    page.wait_for_load_state("networkidle")
    return page