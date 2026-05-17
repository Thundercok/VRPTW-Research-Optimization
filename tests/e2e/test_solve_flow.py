from playwright.sync_api import Page, expect
from pathlib import Path

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
    assert resp.ok

# NOTICE: We are passing 'authed_page' here now!
def test_solomon_list(authed_page: Page):
    resp = authed_page.request.get(f"{BASE}/api/solomon/list")
    assert resp.ok
    data = resp.json()
    datasets = data.get("datasets", data) if isinstance(data, dict) else data
    assert isinstance(datasets, list) and len(datasets) > 0

def test_nexus_v95(authed_page: Page):
    # Navigation and login is already handled by the fixture
    resp = authed_page.request.get(f"{BASE}/api/analysis/nexus?version=v9.5")
    assert resp.ok
    shot(authed_page, "04_nexus_v95")