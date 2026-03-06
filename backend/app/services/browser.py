"""
Browser Service
===============
Manages a singleton Playwright browser + page for the auto-apply agent.
Designed to be used within a Celery task context (one browser per worker).
"""

from __future__ import annotations

import asyncio
from typing import Optional

from playwright.async_api import async_playwright, Browser, Page, Playwright

_playwright: Optional[Playwright] = None
_browser: Optional[Browser] = None
_page: Optional[Page] = None


async def get_page() -> Page:
    """Get or create the singleton browser page."""
    global _playwright, _browser, _page

    if _page and not _page.is_closed():
        return _page

    if not _playwright:
        _playwright = await async_playwright().start()

    if not _browser or not _browser.is_connected():
        _browser = await _playwright.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
            ],
        )

    context = await _browser.new_context(
        viewport={"width": 1280, "height": 800},
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
    )
    _page = await context.new_page()
    return _page


async def close_browser() -> None:
    """Cleanly shut down the browser."""
    global _playwright, _browser, _page
    if _page and not _page.is_closed():
        await _page.close()
    if _browser and _browser.is_connected():
        await _browser.close()
    if _playwright:
        await _playwright.stop()
    _playwright = _browser = _page = None
