#!/usr/bin/env python3
"""Record the PriceWatch portfolio demo video.

Drives the real full-stack app (FastAPI serving the built React UI) inside a
browser, recorded by Playwright's built-in video capture:
  1. branded opening cover,
  2. loads 3 demo products (baseline prices),
  3. runs repeated price checks - prices drift, sparklines build up,
  4. first new-low price triggers a drop alert in the live alerts feed,
  5. highlights drop badges / sparklines / alert channel,
  6. closing card: Telegram + Email alerts, hourly unattended schedule.

Run with any Python that has playwright installed, e.g. the Demo 1 venv:
    ../ai-web-data-extractor/.venv/bin/python scripts/record_demo.py
Output:
    docs/recordings/demo.webm   (convert to docs/demo.gif with ffmpeg)
"""

from __future__ import annotations

import asyncio
import re
import time
from pathlib import Path

from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parent.parent
VIDEO_DIR = ROOT / "docs" / "recordings"
APP_URL = "http://localhost:8010/"

INIT_JS = """
(() => {
  const CSS = `
#pw-banner { position:fixed; top:0; left:0; right:0; z-index:2147483647;
  background:linear-gradient(90deg,#1e3a8a,#2563eb); color:#fff;
  padding:12px 24px; font:600 15px/1.3 -apple-system,'Segoe UI',sans-serif;
  box-shadow:0 3px 14px rgba(0,0,0,.3); letter-spacing:.2px;
  display:flex; align-items:center; gap:10px; }
#pw-banner .dot { width:10px; height:10px; border-radius:50%;
  background:#4ade80; box-shadow:0 0 8px #4ade80; flex:none;
  animation:pwpulse 1s infinite; }
@keyframes pwpulse { 50% { opacity:.35; } }
body { padding-top:54px !important; }
.product-card { transition:box-shadow .3s ease, outline-color .3s ease; }
.product-card.rec-hl { outline:3px solid #16a34a; outline-offset:3px;
  box-shadow:0 0 0 6px rgba(22,163,74,.15), 0 10px 34px rgba(30,58,138,.22) !important; }
.alerts-panel.rec-hl { outline:3px solid #2563eb; outline-offset:3px;
  box-shadow:0 0 0 6px rgba(37,99,235,.15); }
.controls.rec-hl { outline:3px solid #2563eb; outline-offset:3px;
  box-shadow:0 0 0 6px rgba(37,99,235,.15); }
`;
  window.__pwBanner = function (text) {
    let b = document.getElementById('pw-banner');
    if (!b) {
      b = document.createElement('div'); b.id = 'pw-banner';
      b.innerHTML = '<span class="dot"></span><span class="txt"></span>';
      (document.body || document.documentElement).appendChild(b);
    }
    b.querySelector('.txt').textContent = text;
  };
  document.addEventListener('DOMContentLoaded', () => {
    if (document.documentElement.dataset.cover) return;
    const s = document.createElement('style');
    s.textContent = CSS;
    document.head.appendChild(s);
    window.__pwBanner('PriceWatch   ·   Loading app…');
  });
})();
"""

BANNER_JS = "(text) => window.__pwBanner(text)"

COVER_HTML = """<!doctype html>
<html data-cover="1"><head><meta charset="utf-8"><style>
  * { margin:0; box-sizing:border-box; }
  body { height:100vh; background:linear-gradient(135deg,#0f172a 0%,#1e3a8a 100%);
         color:#fff; display:flex; flex-direction:column; align-items:center;
         justify-content:center; font-family:-apple-system,'Segoe UI',sans-serif; }
  .title { font-size:52px; font-weight:800; letter-spacing:.5px; }
  .tagline { margin-top:16px; font-size:19px; opacity:.88; font-weight:400;
             max-width:780px; text-align:center; line-height:1.5; }
  .tags { margin-top:34px; font-size:14px; opacity:.55; letter-spacing:1px; }
  .bar { margin-top:40px; width:280px; height:4px; border-radius:2px;
         background:rgba(255,255,255,.15); overflow:hidden; }
  .bar::after { content:''; display:block; height:100%; width:40%;
         background:#4ade80; border-radius:2px; animation:load 1.6s ease-in-out infinite; }
  @keyframes load { 0% { margin-left:-40%; } 100% { margin-left:100%; } }
</style></head><body>
  <div class="title">PriceWatch</div>
  <div class="tagline">Track product prices on a schedule &mdash; the moment anything
    hits a new low, you get a Telegram or email alert with the full price history.</div>
  <div class="bar"></div>
  <div class="tags">PER-STORE SCRAPERS &middot; SQLITE PRICE HISTORY &middot; DROP DETECTION &middot; TELEGRAM / EMAIL ALERTS</div>
</body></html>"""


async def main() -> None:
    VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    for old in VIDEO_DIR.glob("*.webm"):
        old.unlink()

    t0 = time.time()
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            context = await browser.new_context(
                record_video_dir=str(VIDEO_DIR),
                record_video_size={"width": 1280, "height": 800},
                viewport={"width": 1280, "height": 800},
            )
            await context.add_init_script(INIT_JS)
            page = await context.new_page()
            page.set_default_timeout(30_000)

            # 1. Branded cover (never open on a blank frame).
            await page.set_content(COVER_HTML, wait_until="load")
            await page.wait_for_timeout(2_300)

            # 2. Open the real app - empty watchlist.
            await page.goto(APP_URL, wait_until="domcontentloaded", timeout=20_000)
            await page.wait_for_selector(".track-form", timeout=15_000)
            await page.evaluate(
                BANNER_JS,
                "PriceWatch   ·   Step 1 — Paste any product URL, or load the built-in demo store",
            )
            await page.evaluate("document.querySelector('.controls').classList.add('rec-hl')")
            await page.wait_for_timeout(2_800)

            # 3. Load the 3 demo products at baseline prices.
            await page.evaluate("document.querySelector('.controls').classList.remove('rec-hl')")
            await page.get_by_role("button", name=re.compile("Load 3 demo")).click()
            await page.wait_for_function(
                "document.querySelectorAll('.product-card').length === 3", timeout=15_000
            )
            print("[seed] 3 product cards rendered", flush=True)
            await page.evaluate(
                BANNER_JS,
                "PriceWatch   ·   ✓ 3 products tracked — baseline prices locked in",
            )
            await page.wait_for_timeout(3_200)

            # 4. Run price checks until drops trigger alerts.
            await page.evaluate(
                BANNER_JS,
                "PriceWatch   ·   Step 2 — Running price checks (same job the scheduler runs hourly)…",
            )
            check_btn = page.get_by_role("button", name=re.compile("Check prices"))
            for i in range(6):
                await check_btn.scroll_into_view_if_needed()
                await check_btn.click()
                await page.wait_for_timeout(3_400)
                alerts = await page.locator(".alert-row").count()
                cards = await page.locator(".product-card").count()
                print(f"[check] round {i + 1}: {cards} cards, {alerts} alerts", flush=True)
                if alerts >= 4:
                    break
            await page.wait_for_timeout(2_800)

            # 5. Highlight a card that dropped: green drop badge + sparkline.
            drop_card = page.locator(".product-card", has=page.locator(".badge-drop")).first
            await drop_card.evaluate(
                "el => { el.classList.add('rec-hl'); el.scrollIntoView({behavior:'smooth', block:'center'}); }"
            )
            await page.evaluate(
                BANNER_JS,
                "PriceWatch   ·   ✓ New lowest price detected — drop badge, sparkline and full history",
            )
            await page.wait_for_timeout(5_600)
            await page.evaluate(
                "document.querySelectorAll('.product-card.rec-hl').forEach(c => c.classList.remove('rec-hl'))"
            )

            # 6. Highlight the live alerts feed.
            await page.evaluate(
                "document.querySelector('.alerts-panel').classList.add('rec-hl')"
            )
            await page.locator(".alerts-panel").scroll_into_view_if_needed()
            await page.evaluate(
                BANNER_JS,
                "PriceWatch   ·   Every new-low fires an alert — Telegram, Email, or console fallback",
            )
            await page.wait_for_timeout(4_600)

            # 7. Closing card.
            await page.evaluate(
                "document.querySelector('.alerts-panel').classList.remove('rec-hl')"
            )
            await page.evaluate(
                BANNER_JS,
                "PriceWatch   ·   Runs unattended on a schedule · per-store parsers · one-command Docker deploy",
            )
            await page.wait_for_timeout(7_000)

            video = page.video
            await context.close()
            webm_path = Path(await video.path()) if video else None
        finally:
            await browser.close()

    final = VIDEO_DIR / "demo.webm"
    if webm_path and webm_path != final:
        webm_path.rename(final)
    print(f"\nDONE in {time.time() - t0:.0f}s", flush=True)
    print(f"video: {final}", flush=True)


if __name__ == "__main__":
    asyncio.run(asyncio.wait_for(main(), timeout=180))
