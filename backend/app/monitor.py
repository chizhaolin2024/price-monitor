from . import db
from .config import settings
from .notifiers import notify
from .scrapers import get_scraper


async def run_check() -> dict:
    result = {"checked": 0, "errors": [], "alerts": []}
    with db.get_db() as conn:
        products = db.list_products(conn)

    for product in products:
        scraper = get_scraper(product["url"])
        if scraper is None:
            snapshot_error = "no scraper registered for this store"
            with db.get_db() as conn:
                db.add_history(conn, product["id"], None, False, "error", snapshot_error)
            result["errors"].append({"product_id": product["id"], "title": product["title"], "error": snapshot_error})
            continue

        snapshot = await scraper.fetch(product["url"])

        with db.get_db() as conn:
            previous_lowest = db.lowest_price_before(conn, product["id"])
            db.add_history(
                conn,
                product["id"],
                snapshot.price,
                snapshot.in_stock,
                snapshot.status,
                snapshot.error,
            )

            if snapshot.status != "ok" or snapshot.price is None:
                result["errors"].append({
                    "product_id": product["id"],
                    "title": product["title"],
                    "error": snapshot.error or "price unavailable",
                })
                continue

            result["checked"] += 1
            title = snapshot.title or product["title"]
            currency = snapshot.currency or product["currency"]

            if previous_lowest is not None and snapshot.price < previous_lowest - 0.009:
                drop_pct = (previous_lowest - snapshot.price) / previous_lowest * 100
                message = (
                    f"Price drop alert: {title}\n"
                    f"{currency} {previous_lowest:.2f} -> {currency} {snapshot.price:.2f} "
                    f"(-{drop_pct:.1f}%)\n{product['url']}"
                )
                channels = await notify(settings, f"Price drop: {title}", message)
                alert_id = db.add_alert(
                    conn,
                    product["id"],
                    title,
                    previous_lowest,
                    snapshot.price,
                    currency,
                    ",".join(channels),
                    message,
                )
                result["alerts"].append({
                    "id": alert_id,
                    "product_id": product["id"],
                    "title": title,
                    "old_price": previous_lowest,
                    "new_price": snapshot.price,
                    "currency": currency,
                    "channels": channels,
                })

    return result
