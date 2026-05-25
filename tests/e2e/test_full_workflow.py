from pathlib import Path

import pytest
from playwright.sync_api import Page, expect

SCREENSHOTS = Path("tests/e2e/screenshots")
SCREENSHOTS.mkdir(parents=True, exist_ok=True)


def shot(page: Page, name: str) -> None:
    page.screenshot(path=str(SCREENSHOTS / f"{name}.png"), full_page=True)


# Override browser context args for this test file to record video
@pytest.fixture
def browser_context_args(browser_context_args):
    video_dir = Path("tests/e2e/videos")
    video_dir.mkdir(parents=True, exist_ok=True)
    return {
        **browser_context_args,
        "record_video_dir": str(video_dir.resolve()),
        "record_video_size": {"width": 1280, "height": 720},
    }


def test_record_full_app_workflow(authed_page: Page):
    page = authed_page

    # --- Step 1: Initial Load & Live Dispatch Page ---
    print("\n[E2E] Waiting for app shell to render...")
    page.wait_for_selector("#app-shell", state="visible", timeout=15000)
    # Wait to ensure Leaflet map and initial view components are fully drawn
    page.wait_for_timeout(2000)
    shot(page, "01_live_dispatch_initial")

    # --- Step 2: Load Demo Solomon Dataset ---
    print("[E2E] Verifying that Solomon dataset customer rows populate...")
    page.wait_for_selector("#customer-rows tr", state="attached", timeout=10000)
    shot(page, "02_dataset_loaded")

    # --- Step 3: Execute Optimization Pipeline ---
    print("[E2E] Triggering / waiting for solver execution...")
    # App.js may auto-start solving on load, or we trigger it manually
    try:
        # Wait a short moment to see if loading overlay is already visible
        page.wait_for_selector("#loading", state="visible", timeout=1500)
        print("[E2E] Found auto-triggered solver execution.")
        shot(page, "03_optimizing")
    except Exception:
        # If not already running, click "Execute DDQN Solver"
        print("[E2E] Clicking Run Model button manually...")
        if page.locator("#loading").is_hidden():
            page.click("#run-model")
            page.wait_for_selector("#loading", state="visible", timeout=5000)
            shot(page, "03_optimizing")

    # Wait for the optimization job to finish (hide loading screen)
    print("[E2E] Waiting for solver to finish...")
    page.wait_for_selector("#loading", state="hidden", timeout=30000)
    page.wait_for_timeout(1000)
    shot(page, "04_optimization_complete")

    # --- Step 4: Dispatch Simulation Playback & Drawer ---
    print("[E2E] Verifying simulation player and playing route simulation...")
    expect(page.locator("#sim-control-panel")).to_be_visible(timeout=10000)

    # Toggle waypoints manifest drawer
    print("[E2E] Toggling manifest drawer...")
    page.click("#btn-toggle-drawer")
    page.wait_for_timeout(500)
    shot(page, "05_drawer_open")

    page.click("#btn-close-drawer")
    page.wait_for_timeout(500)

    # Play simulation
    page.click("#btn-sim-play")
    print("[E2E] Simulation running. Waiting to record motion...")
    page.wait_for_timeout(2500)
    shot(page, "06_simulation_running")

    # --- Step 5: Fleet Configuration View ---
    print("[E2E] Switching to Fleet Configuration view...")
    page.click('a[data-view="fleet"]')
    page.wait_for_selector("#view-fleet", state="visible", timeout=5000)
    page.wait_for_timeout(1000)
    shot(page, "07_fleet_config")

    # --- Step 6: Model Analytics & Diagnostics ---
    print("[E2E] Switching to Model Analytics & Diagnostics view...")
    page.click('a[data-view="analytics"]')
    page.wait_for_selector("#view-analytics", state="visible", timeout=5000)
    # Wait for version selector options to load
    page.wait_for_selector("#analysis-version option", state="attached", timeout=10000)
    page.wait_for_timeout(2000)
    shot(page, "08_model_analytics")

    # Open deep diagnostics modal
    print("[E2E] Opening Deep Diagnostics modal...")
    page.click("#analysis-open-popup")
    page.wait_for_selector("#analysis-modal", state="visible", timeout=5000)
    page.wait_for_timeout(1000)
    shot(page, "09_deep_diagnostics_modal")

    # Close modal
    print("[E2E] Closing Deep Diagnostics modal...")
    page.click("#analysis-modal-close")
    page.wait_for_selector("#analysis-modal", state="hidden", timeout=5000)
    page.wait_for_timeout(500)

    # --- Step 7: System Settings ---
    print("[E2E] Switching to System Settings view...")
    page.click('a[data-view="settings"]')
    page.wait_for_selector("#view-settings", state="visible", timeout=5000)
    page.wait_for_timeout(1000)
    shot(page, "10_settings")

    # --- Step 8: Sign Out ---
    print("[E2E] Logging out...")
    page.click("#btn-logout")
    page.wait_for_selector("#auth-screen", state="visible", timeout=10000)
    page.wait_for_timeout(1000)
    shot(page, "11_logged_out")
    print("[E2E] Test complete!")
