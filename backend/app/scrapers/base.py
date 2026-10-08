from dataclasses import dataclass


@dataclass
class Snapshot:
    title: str
    price: float | None
    currency: str
    in_stock: bool
    status: str
    error: str = ""


class BaseScraper:
    name: str = "base"

    def handles(self, url: str) -> bool:
        raise NotImplementedError

    async def fetch(self, url: str) -> Snapshot:
        raise NotImplementedError
