from .base import BaseScraper, Snapshot
from .demo import DEMO_PRODUCTS, SEED_URLS, DemoScraper
from .toscrape import TosScrapeScraper

_SCRAPERS: list[BaseScraper] = [DemoScraper(), TosScrapeScraper()]


def get_scraper(url: str) -> BaseScraper | None:
    for scraper in _SCRAPERS:
        if scraper.handles(url):
            return scraper
    return None


def supported_hint() -> str:
    return "Supported sources: demo://<product> (built-in demo store) or product pages on books.toscrape.com"


__all__ = ["BaseScraper", "Snapshot", "DemoScraper", "TosScrapeScraper", "DEMO_PRODUCTS", "SEED_URLS",
           "get_scraper", "supported_hint"]
