import re

import httpx
from bs4 import BeautifulSoup

from .base import BaseScraper, Snapshot

CURRENCY_MAP = {"£": "GBP", "$": "USD", "€": "EUR"}


class TosScrapeScraper(BaseScraper):
    name = "books.toscrape.com"

    def handles(self, url: str) -> bool:
        return "books.toscrape.com" in url

    async def fetch(self, url: str) -> Snapshot:
        try:
            async with httpx.AsyncClient(timeout=15, follow_redirects=True,
                                         headers={"User-Agent": "PriceWatch/1.0 (+demo)"}) as client:
                resp = await client.get(url)
                resp.raise_for_status()
        except Exception as exc:
            return Snapshot(title="", price=None, currency="GBP", in_stock=False,
                            status="error", error=f"fetch failed: {type(exc).__name__}")

        soup = BeautifulSoup(resp.text, "html.parser")
        title_el = soup.select_one(".product_main h1")
        price_el = soup.select_one(".product_main .price_color")
        if not title_el or not price_el:
            return Snapshot(title="", price=None, currency="GBP", in_stock=False,
                            status="error", error="could not parse product page")

        price_text = price_el.get_text(strip=True)
        currency = "GBP"
        for symbol, code in CURRENCY_MAP.items():
            if symbol in price_text:
                currency = code
                break
        match = re.search(r"\d+(?:\.\d+)?", price_text.replace(",", ""))
        if not match:
            return Snapshot(title=title_el.get_text(strip=True), price=None, currency=currency,
                            in_stock=False, status="error", error=f"could not parse price '{price_text}'")
        availability = soup.select_one(".product_main .availability")
        in_stock = bool(availability and "in stock" in availability.get_text().lower())
        return Snapshot(
            title=title_el.get_text(strip=True),
            price=float(match.group(0)),
            currency=currency,
            in_stock=in_stock,
            status="ok",
        )
