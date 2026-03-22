"""
Takes screenshots of the dashboard for README documentation.
Requires: pip install playwright && python -m playwright install chromium

Usage:
    # Make sure the server is running on port 8100 first
    python screenshot.py
"""

from playwright.sync_api import sync_playwright


def take_screenshots():
    with sync_playwright() as p:
        browser = p.chromium.launch()

        # ── Light mode screenshot ──
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto("http://localhost:8100")
        page.wait_for_timeout(1500)

        # Click all service cards to expand them
        cards = page.query_selector_all(".service-card")
        for card in cards:
            card.click()
        page.wait_for_timeout(500)

        page.screenshot(path="docs/screenshot-light.png", full_page=True)
        print("Saved: docs/screenshot-light.png")
        page.close()

        # ── Dark mode screenshot ──
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto("http://localhost:8100")
        page.wait_for_timeout(1500)

        # Toggle dark mode
        page.click(".btn-theme")
        page.wait_for_timeout(300)

        # Expand all cards
        cards = page.query_selector_all(".service-card")
        for card in cards:
            card.click()
        page.wait_for_timeout(500)

        page.screenshot(path="docs/screenshot-dark.png", full_page=True)
        print("Saved: docs/screenshot-dark.png")
        page.close()

        browser.close()
        print("\nDone! Screenshots saved in docs/ directory.")


if __name__ == "__main__":
    take_screenshots()
