import random

from .base import BaseScraper, Snapshot

DEMO_PRODUCTS: dict[str, tuple[str, float]] = {
    "noise-canceling-headphones": ("SoundCore Noise-Canceling Headphones", 199.00),
    "espresso-machine": ("BaristaPro Espresso Machine", 349.00),
    "mechanical-keyboard": ("Tactile75 Mechanical Keyboard", 129.00),
    "4k-monitor": ('ViewMax 27" 4K Monitor', 279.00),
    "standing-desk": ("ErgoLift Standing Desk", 499.00),
    "wireless-mouse": ("Glide Wireless Mouse", 49.00),
}

SEED_URLS = [f"demo://{sku}" for sku in ("noise-canceling-headphones", "espresso-machine", "mechanical-keyboard")]


class DemoScraper(BaseScraper):
    name = "demo-store"

    def __init__(self) -> None:
        self._state: dict[str, float] = {}

    def handles(self, url: str) -> bool:
        return url.startswith("demo://")

    async def fetch(self, url: str) -> Snapshot:
        sku = url.split("://", 1)[1].strip("/")
        item = DEMO_PRODUCTS.get(sku)
        if not item:
            return Snapshot(title=sku, price=None, currency="USD", in_stock=False, status="error",
                            error=f"unknown demo product '{sku}'")
        title, base_price = item
        if sku not in self._state:
            self._state[sku] = base_price
            return Snapshot(title=title, price=base_price, currency="USD", in_stock=True, status="ok")
        price = self._state[sku]
        roll = random.random()
        if roll < 0.30:
            price *= random.uniform(0.85, 0.94)
        elif roll < 0.80:
            price *= random.uniform(0.99, 1.03)
        else:
            price *= random.uniform(1.02, 1.08)
        price = round(min(base_price * 1.30, max(base_price * 0.50, price)), 2)
        self._state[sku] = price
        return Snapshot(title=title, price=price, currency="USD", in_stock=True, status="ok")
