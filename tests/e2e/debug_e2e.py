import os
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

HOSTING_BASE = "http://127.0.0.1:5050"
TEST_EMAIL = "test@vrptw.local"
TEST_PASSWORD = "testpass123"

def run_debug():
    with sync_playwright() as p:
        print("[DEBUG] Launching headless browser...")
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        print("[DEBUG] Loading login page...")
        page.goto(f"{HOSTING_BASE}/auth.html")
        page.wait_for_load_state("networkidle")
        
        print("[DEBUG] Logging in...")
        page.fill("#login-email", TEST_EMAIL)
        page.fill("#login-password", TEST_PASSWORD)
        page.click("#btn-login")
        
        print("[DEBUG] Waiting for app shell...")
        page.wait_for_selector("#app-shell", state="visible", timeout=15000)
        
        # Dismiss help modal
        try:
            page.wait_for_selector("#help-modal-close", state="visible", timeout=2000)
            page.click("#help-modal-close")
            print("[DEBUG] Help modal dismissed.")
        except Exception:
            pass

        # Wait for auto-optimization
        try:
            page.wait_for_selector("#loading", state="visible", timeout=2000)
            print("[DEBUG] Auto-optimization active. Waiting for completion...")
            page.wait_for_selector("#loading", state="hidden", timeout=30000)
        except Exception:
            print("[DEBUG] No auto-optimization active.")

        # Choose dataset
        print("[DEBUG] Selecting dataset...")
        page.select_option("#dataset-select", "c1_demo")
        page.wait_for_timeout(1000)
        page.wait_for_selector("#customer-rows tr", state="attached", timeout=10000)

        # Set sliders
        page.fill("#vehicles-slider", "3")
        page.fill("#capacity-slider", "100")
        page.wait_for_timeout(500)

        # Run optimization
        print("[DEBUG] Running optimization solver...")
        page.click("#run-model")
        page.wait_for_selector("#loading", state="visible", timeout=5000)
        page.wait_for_selector("#loading", state="hidden", timeout=30000)
        page.wait_for_timeout(1000)

        # Open driver app
        print("[DEBUG] Opening Driver App Companion...")
        page.click("#btn-toggle-driver-app")
        page.wait_for_selector("#driver-app-emulator", state="visible", timeout=5000)

        # Print dropdown options
        dropdown_html = page.eval_on_selector("#driver-app-select", "el => el.innerHTML")
        print("\n=== Dropdown Options ===")
        print(dropdown_html)
        print("========================\n")

        # Select Driver 1
        print("[DEBUG] Selecting Driver at index 1...")
        page.select_option("#driver-app-select", index=1)
        page.wait_for_timeout(1000)

        # Print companion content
        content_html = page.eval_on_selector("#driver-app-content", "el => el.innerHTML")
        print("=== Driver App Content ===")
        print(content_html)
        print("==========================\n")

        browser.close()

if __name__ == "__main__":
    run_debug()
