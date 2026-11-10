#!/usr/bin/env python3
"""Capture the local Tripwire dashboard and the public GitHub repo page."""
from __future__ import annotations

import re
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / "video/build/work"
WORK.mkdir(parents=True, exist_ok=True)

TOKEN_RE = re.compile(r"otk_[A-Za-z0-9_\-]+|tk-[A-Za-z0-9_\-]+|Bearer\s+\S+")


def _scan(path: Path) -> None:
    raw = path.read_bytes()
    # PNG text chunks / trailing strings
    if TOKEN_RE.search(raw.decode("latin-1", "ignore")):
        raise SystemExit(f"token-like string found in {path}")


def main() -> None:
    dash_dir = WORK / "dashboard"
    dash_dir.mkdir(exist_ok=True)
    with sync_playwright() as p:
        chrome = Path("/home/box/.cache/ms-playwright/chromium-1248/chrome-linux64/chrome")
        executable = str(chrome) if chrome.exists() else "/usr/bin/google-chrome"
        browser = p.chromium.launch(
            headless=True,
            executable_path=executable,
            args=["--no-sandbox", "--disable-gpu", "--hide-scrollbars"],
        )
        # Local dashboard
        page = browser.new_page(viewport={"width": 1920, "height": 1080}, device_scale_factor=1)
        page.goto("http://127.0.0.1:8000/", wait_until="networkidle", timeout=30000)
        page.wait_for_selector("#banner")
        page.wait_for_function("() => document.getElementById('banner').textContent.includes('LIVE')")
        page.wait_for_function("() => document.querySelectorAll('#decisions tr').length > 3")
        time.sleep(0.4)
        dest = dash_dir / "overview.png"
        page.screenshot(path=str(dest), full_page=False)
        _scan(dest)

        # Verify audit chain so the audit line is populated
        page.click("#verify")
        page.wait_for_function("() => (document.getElementById('auditLine').textContent || '').includes('Audit chain')")
        time.sleep(0.2)
        dest = dash_dir / "audit.png"
        page.screenshot(path=str(dest), full_page=False)
        _scan(dest)

        # Scroll to holds and capture before/after approve
        page.evaluate("document.querySelector('#holds').scrollIntoView({block: 'center'})")
        time.sleep(0.2)
        dest = dash_dir / "holds_open.png"
        page.screenshot(path=str(dest), full_page=False)
        _scan(dest)

        approve = page.locator("button[data-approve]").first
        if approve.count():
            approve.click()
            page.wait_for_timeout(400)
            dest = dash_dir / "holds_approved.png"
            page.screenshot(path=str(dest), full_page=False)
            _scan(dest)

        # Scroll features list
        page.evaluate("document.querySelector('#features').scrollIntoView({block: 'center'})")
        time.sleep(0.2)
        dest = dash_dir / "features.png"
        page.screenshot(path=str(dest), full_page=False)
        _scan(dest)

        page.close()

        # Public GitHub repo, incognito-style (fresh context, no stored auth)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            device_scale_factor=1,
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        gh = context.new_page()
        gh.goto("https://github.com/Cubiczan/tripwire-otari", wait_until="domcontentloaded", timeout=60000)
        # Dismiss cookie/consent if it appears
        for label in ("Accept", "Accept all", "Accept cookies", "Got it"):
            btn = gh.get_by_role("button", name=re.compile(label, re.I))
            try:
                if btn.count() and btn.first.is_visible(timeout=1500):
                    btn.first.click()
                    break
            except Exception:
                pass
        gh.wait_for_selector("text=tripwire-otari", timeout=30000)
        time.sleep(1.0)
        dest = WORK / "github_repo.png"
        gh.screenshot(path=str(dest), full_page=False)
        _scan(dest)
        context.close()
        browser.close()
    print("screenshots ok")


if __name__ == "__main__":
    main()
