import asyncio
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import db, monitor
from .config import settings
from .scrapers import DEMO_PRODUCTS, SEED_URLS, get_scraper, supported_hint


class TrackIn(BaseModel):
    url: str


def serialize_product(conn, product: dict) -> dict:
    history = db.history_rows(conn, product["id"])
    prices = [h["price"] for h in history if h["price"] is not None]
    latest = history[-1] if history else None
    return {
        "id": product["id"],
        "url": product["url"],
        "store": product["store"],
        "title": product["title"],
        "currency": product["currency"],
        "initial_price": prices[0] if prices else None,
        "lowest_price": min(prices) if prices else None,
        "latest_price": latest["price"] if latest else None,
        "status": latest["status"] if latest else "pending",
        "in_stock": bool(latest["in_stock"]) if latest else True,
        "last_error": latest["error"] if latest and latest["status"] == "error" else "",
        "last_checked": latest["checked_at"] if latest else None,
        "created_at": product["created_at"],
        "history": [{"price": h["price"], "checked_at": h["checked_at"]} for h in history],
    }


async def _track_url(url: str) -> dict:
    url = url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")
    scraper = get_scraper(url)
    if scraper is None:
        raise HTTPException(status_code=400, detail=f"Unsupported store. {supported_hint()}")

    snapshot = await scraper.fetch(url)
    if snapshot.status != "ok" or snapshot.price is None:
        raise HTTPException(status_code=502, detail=f"Could not read product page: {snapshot.error or 'price unavailable'}")

    with db.get_db() as conn:
        product, created = db.get_or_create_product(conn, url, scraper.name, snapshot.title, snapshot.currency)
        if created:
            db.add_history(conn, product["id"], snapshot.price, snapshot.in_stock, "ok")
        return serialize_product(conn, product)


async def scheduler_loop() -> None:
    while True:
        await asyncio.sleep(settings.check_interval_seconds)
        try:
            result = await monitor.run_check()
            print(f"[scheduler] checked={result['checked']} alerts={len(result['alerts'])} errors={len(result['errors'])}")
        except Exception as exc:
            print(f"[scheduler] check failed: {type(exc).__name__}: {exc}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    app.state.check_lock = asyncio.Lock()
    app.state.scheduler_task = asyncio.create_task(scheduler_loop())
    yield
    app.state.scheduler_task.cancel()


app = FastAPI(title="PriceWatch", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health() -> dict:
    return {
        "status": "ok",
        "time": time.time(),
        "check_interval_seconds": settings.check_interval_seconds,
        "telegram_configured": settings.telegram_configured,
        "email_configured": settings.email_configured,
        "demo_catalog": [{"url": f"demo://{sku}", "title": title, "price": price}
                         for sku, (title, price) in DEMO_PRODUCTS.items()],
    }


@app.get("/api/products")
async def get_products() -> list[dict]:
    with db.get_db() as conn:
        return [serialize_product(conn, p) for p in db.list_products(conn)]


@app.post("/api/products")
async def track_product(body: TrackIn) -> dict:
    return await _track_url(body.url)


@app.post("/api/products/seed")
async def seed_demo_products() -> dict:
    products = []
    for url in SEED_URLS:
        try:
            products.append(await _track_url(url))
        except HTTPException:
            continue
    return {"added": len(products), "products": products}


@app.delete("/api/products/{product_id}")
async def remove_product(product_id: int) -> dict:
    with db.get_db() as conn:
        db.delete_product(conn, product_id)
    return {"deleted": product_id}


@app.post("/api/check")
async def check_now() -> dict:
    if app.state.check_lock.locked():
        return {"status": "already_running"}
    async with app.state.check_lock:
        return await monitor.run_check()


@app.get("/api/alerts")
async def get_alerts() -> list[dict]:
    with db.get_db() as conn:
        return db.list_alerts(conn)


static_path = Path(settings.static_dir)
if static_path.is_dir():
    app.mount("/assets", StaticFiles(directory=static_path / "assets"), name="assets")

    @app.get("/")
    async def index() -> FileResponse:
        return FileResponse(static_path / "index.html")

    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str) -> FileResponse:
        target = static_path / full_path
        if target.is_file():
            return FileResponse(target)
        return FileResponse(static_path / "index.html")
