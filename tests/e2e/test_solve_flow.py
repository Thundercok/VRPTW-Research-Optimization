from playwright.sync_api import Page, expect
from pathlib import Path
import time

SCREENSHOTS = Path("tests/e2e/screenshots")
SCREENSHOTS.mkdir(parents=True, exist_ok=True)

BASE = "http://127.0.0.1:8000"


def shot(page: Page, name: str) -> None:
    page.screenshot(path=str(SCREENSHOTS / f"{name}.png"), full_page=True)


def test_landing_page(page: Page):
    page.goto(BASE)
    page.wait_for_load_state("networkidle")
    shot(page, "01_landing")
    expect(page).not_to_have_title("")


def test_app_loads(page: Page):
    page.goto(f"{BASE}/app.html")
    page.wait_for_load_state("networkidle")
    shot(page, "02_app_initial")


def test_api_health(page: Page):
    resp = page.request.get(f"{BASE}/api/health")
    assert resp.ok, f"Health check failed: {resp.status}"


def test_solomon_list(page: Page):
    resp = page.request.get(f"{BASE}/api/solomon/list")
    assert resp.ok
    data = resp.json()
    # Fix: Extract 'datasets' since the API returns a dict, not a bare list
    datasets = data.get("datasets", data) if isinstance(data, dict) else data
    assert isinstance(datasets, list) and len(datasets) > 0, "Solomon list empty"


def test_demo_instance_loads(page: Page):
    page.goto(f"{BASE}/app.html")
    page.wait_for_load_state("networkidle")
    shot(page, "03_app_with_demo")

    resp = page.request.get(f"{BASE}/api/solomon?name=demo")
    assert resp.ok, f"Demo instance failed: {resp.status}"


def test_analysis_versions(page: Page):
    resp = page.request.get(f"{BASE}/api/analysis/versions")
    assert resp.ok
    data = resp.json()
    assert data, "No analysis versions returned"


# Replaced the guest bypass logic with the authed_page fixture
def test_nexus_v95(authed_page: Page):
    # Navigation, login typing, and wait states are completely handled by the fixture
    resp = authed_page.request.get(f"{BASE}/api/analysis/nexus?version=v9.5")
    assert resp.ok, f"Nexus v9.5 failed: {resp.status}"
    shot(authed_page, "04_nexus_v95")
    

def test_activity_feed(page: Page):
    resp = page.request.get(f"{BASE}/api/analysis/activity?hours=24")
    assert resp.ok
    shot_needed = False  # API-only, no UI state to capture
    _ = shot_needed