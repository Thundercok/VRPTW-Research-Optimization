import os
from pathlib import Path

import pytest
from dotenv import load_dotenv
from playwright.sync_api import Page, expect

load_dotenv(".env.test")
HOSTING_BASE = "http://127.0.0.1:5050"
TEST_EMAIL = os.getenv("TEST_EMAIL", "test@vrptw.local")
TEST_PASSWORD = os.getenv("TEST_PASSWORD", "testpass123")

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


def test_record_full_app_workflow(page: Page):
    # Enable console logs in python runner for debugging
    page.on("console", lambda msg: print(f"\n[Console]: {msg.text}"))
    page.on("pageerror", lambda err: print(f"\n[FATAL JS ERROR]: {err}"))

    # --- Step 1: Initial Load of Login Page ---
    print("\n[E2E] Loading auth page...")
    page.goto(f"{HOSTING_BASE}/auth.html")
    page.wait_for_load_state("networkidle")
    shot(page, "01_auth_page_loaded")
    expect(page.locator("#auth-screen")).to_be_visible()

    # --- Step 2: Log In ---
    print(f"[E2E] Logging in with {TEST_EMAIL}...")
    page.fill("#login-email", TEST_EMAIL)
    page.fill("#login-password", TEST_PASSWORD)
    shot(page, "02_login_fields_filled")

    page.click("#btn-login")

    # Wait for the redirection and the app shell to render
    print("[E2E] Waiting for redirection and app shell...")
    page.wait_for_selector("#app-shell", state="visible", timeout=15000)
    shot(page, "03_app_shell_loaded")

    # Dismiss the help modal if it appears
    try:
        page.wait_for_selector("#help-modal-close", state="visible", timeout=3000)
        page.click("#help-modal-close")
        print("[E2E] Help modal dismissed.")
    except Exception:
        pass

    page.wait_for_timeout(500)

    # --- Step 3: Handle Auto-Optimization on Load ---
    # Wait for any initial auto-optimization solver step to hide.
    try:
        print("[E2E] Checking if initial auto-optimization starts...")
        page.wait_for_selector("#loading", state="visible", timeout=2000)
        print("[E2E] Auto-optimization running. Waiting for completion...")
        page.wait_for_selector("#loading", state="hidden", timeout=30000)
        print("[E2E] Auto-optimization finished.")
    except Exception:
        print("[E2E] No initial auto-optimization active.")

    shot(page, "04_dashboard_ready")

    # --- Step 4: Choose a Dataset & Set Sliders ---
    print("[E2E] Selecting C1 Solomon dataset...")
    page.select_option("#dataset-select", "c1_demo")
    page.wait_for_timeout(1000)  # Wait for API fetch and render
    page.wait_for_selector("#customer-rows tr", state="attached", timeout=10000)
    shot(page, "05_c1_dataset_loaded")

    # Customize fleet parameters via sliders to simulate user configuration
    print("[E2E] Adjusting vehicles and capacity parameters...")
    page.fill("#vehicles-slider", "3")
    page.fill("#capacity-slider", "100")
    page.wait_for_timeout(500)
    shot(page, "06_fleet_parameters_configured")

    # --- Step 5: Execute Optimization Pipeline Manually ---
    print("[E2E] Clicking Run Model button manually...")
    page.click("#run-model")
    page.wait_for_selector("#loading", state="visible", timeout=5000)
    shot(page, "07_solver_running")

    # Wait for solver to complete
    print("[E2E] Waiting for solver to finish...")
    page.wait_for_selector("#loading", state="hidden", timeout=30000)
    page.wait_for_timeout(1000)
    shot(page, "08_optimization_complete")

    # --- Step 6: Dispatch Simulation Playback ---
    print("[E2E] Verifying simulation player and playing route simulation...")
    expect(page.locator("#sim-control-panel")).to_be_visible(timeout=10000)

    # Play simulation to show motion on the map
    page.click("#btn-sim-play")
    print("[E2E] Simulation running. Waiting to record motion...")
    page.wait_for_timeout(2000)
    shot(page, "09_simulation_running")

    # Pause simulation to stabilize DOM for driver companion app interaction
    print("[E2E] Pausing simulation for driver interaction...")
    page.click("#btn-sim-play")
    page.wait_for_timeout(500)
    shot(page, "10_simulation_paused")

    # Reset simulation clock to 0 using the exposed window.app instance
    print("[E2E] Resetting simulation clock to 0...")
    page.evaluate(
        "() => { if(window.app && window.app.simulationController) { window.app.simulationController.scrub(0); } }"
    )
    page.wait_for_timeout(500)

    # --- Step 7: Driver App Companion Emulator Interaction ---
    print("[E2E] Opening Driver App Companion emulator...")
    page.click("#btn-toggle-driver-app")
    page.wait_for_selector("#driver-app-emulator", state="visible", timeout=5000)
    page.wait_for_timeout(500)
    shot(page, "11_driver_app_opened")

    # Select the first driver from the selector dropdown
    print("[E2E] Selecting Driver 1...")
    page.select_option("#driver-app-select", index=1)
    page.wait_for_timeout(1000)
    shot(page, "12_driver_selected")

    # Click "Trigger Arrival Now" to arrive at the first stop
    print("[E2E] Triggering stop arrival...")
    page.locator("#driver-app-content .btn-arrive-stop").first.click()
    page.wait_for_timeout(1000)
    shot(page, "13_stop_arrived")

    # Click "Complete Delivery" to open the Proof of Delivery modal
    print("[E2E] Completing stop delivery...")
    page.locator("#driver-app-content .btn-complete-stop").first.click()
    page.wait_for_selector("#pod-proof-modal", state="visible", timeout=5000)
    page.wait_for_timeout(1500)
    shot(page, "14_proof_of_delivery_modal")

    # Close Proof of Delivery modal
    print("[E2E] Closing POD modal...")
    page.click("#btn-close-pod")
    page.wait_for_selector("#pod-proof-modal", state="hidden", timeout=5000)
    page.wait_for_timeout(500)
    shot(page, "15_pod_modal_closed")

    # Resume simulation to let it run the remaining stops
    print("[E2E] Resuming simulation playback...")
    page.click("#btn-sim-play")
    page.wait_for_timeout(2000)
    shot(page, "15b_simulation_resumed")

    # --- Step 8: Toggle Manifest Waypoints Drawer ---
    print("[E2E] Toggling manifest drawer...")
    page.click("#btn-toggle-drawer")
    page.wait_for_timeout(1000)
    shot(page, "16_drawer_open")

    page.click("#btn-close-drawer")
    page.wait_for_timeout(500)

    # --- Step 9: Sign Out ---
    print("[E2E] Logging out...")
    page.click("#btn-logout")
    page.wait_for_selector("#auth-screen", state="visible", timeout=10000)
    page.wait_for_timeout(1000)
    shot(page, "17_logged_out")
    print("[E2E] Operational user test complete!")
