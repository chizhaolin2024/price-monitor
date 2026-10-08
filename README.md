# PriceWatch — Automated Price Monitoring

Track product prices across online stores and get a **Telegram or email alert the moment a price drops to a new low**. Runs unattended on a schedule, keeps full price history in SQLite, and ships with a small web UI for managing your watchlist.

Built as a production-style automation project: per-store scraper modules, failure isolation, health-check friendly behavior, and one-command Docker deployment.

---

## Features

- **Track any product by URL** — paste a product link; the matching store parser fetches title and current price
- **Scheduled checks** — runs every hour by default (configurable), plus a "check now" button
- **Price-drop alerts** — fires only when a product hits a **new all-time low** (no noise from random fluctuations), delivered via **Telegram**, **email (SMTP)**, or the built-in console feed
- **Price history** — every check is stored in SQLite; the UI renders sparklines and tracks initial / lowest / latest price
- **Failure isolation** — a broken or blocked store is flagged in the UI and logged; it never crashes the run or silently produces bad data
- **Pluggable scrapers** — each store is an isolated parser module, so a layout change on one site never affects the others; adding a store takes ~30 lines
- **Web UI** — watchlist cards, drop badges, live alerts feed, one-click removal (React + TypeScript)
- **Polite by design** — public listing pages only, gentle request rates, no login bypassing, no CAPTCHA solving

## Architecture

```
┌──────────────┐      ┌───────────────┐      ┌────────────────────┐
│  React UI    │─────▶│   FastAPI     │─────▶│  Scrapers          │
│  watchlist,  │      │   REST API    │      │  (per-store        │
│  sparklines, │◀─────│               │      │   parser modules)  │
│  alerts feed │      ├───────────────┤      └────────┬───────────┘
└──────────────┘      │  SQLite       │◀──────────────┘
                      │  products /   │
┌──────────────┐      │  price_history│      ┌────────────────────┐
│  Scheduler   │─────▶│  / alerts     │─────▶│  Notifiers         │
│  hourly loop │      └───────────────┘      │  Telegram / Email  │
└──────────────┘                             └────────────────────┘
```

**Stack:** Python · FastAPI · httpx + BeautifulSoup (with Playwright-ready parser base) · SQLite · React + TypeScript + Vite · Docker Compose

## Quick start (Docker)

```bash
cp backend/.env.example backend/.env   # optional: add Telegram/SMTP credentials
docker compose up --build
# open http://localhost:8000
```

The SQLite database persists in `./data/`.

## Quick start (local dev)

```bash
# backend
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --port 8010 --reload

# frontend (separate terminal)
cd frontend
npm install
npm run dev
# open http://localhost:5174
```

## Try it in 30 seconds

1. Open the UI and click **"Load 3 demo products"** (a built-in simulated store — no network needed)
2. Click **"Check prices now"** a few times — prices random-walk and drops trigger alerts
3. Watch the **Alerts** panel populate with drop events
4. Or track a **real** product: paste any book URL from `books.toscrape.com` (e.g. `https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html`) — parsed live over HTTP

## Configuration (`backend/.env`)

| Variable | Purpose | Default |
|---|---|---|
| `CHECK_INTERVAL_SECONDS` | Background check interval | `3600` (hourly) |
| `TELEGRAM_BOT_TOKEN` | Bot token from @BotFather | empty (alerts → console) |
| `TELEGRAM_CHAT_ID` | Your Telegram chat id | empty |
| `SMTP_HOST` / `SMTP_PORT` / `SMTP_USER` / `SMTP_PASSWORD` | SMTP server for email alerts | empty |
| `ALERT_EMAIL_TO` / `ALERT_EMAIL_FROM` | Recipient / sender addresses | empty |
| `DB_PATH` | SQLite file location | `backend/data/pricewatch.db` |

When no notifier is configured, alerts are printed to the server console and still appear in the UI — handy for local demos.

## API

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/health` | Status, notifier configuration, demo catalog |
| `GET` | `/api/products` | Watchlist with latest/lowest/initial prices and history |
| `POST` | `/api/products` | Track a product: `{"url": "..."}` |
| `POST` | `/api/products/seed` | Load the 3 built-in demo products |
| `DELETE` | `/api/products/{id}` | Stop tracking a product |
| `POST` | `/api/check` | Run a price check immediately |
| `GET` | `/api/alerts` | Recent price-drop alerts |

## Adding a new store

Create a scraper class in `backend/app/scrapers/` implementing `handles(url)` and `async fetch(url) -> Snapshot(title, price, currency, in_stock, status)`, then register it in `scrapers/__init__.py`. JS-heavy stores can use Playwright inside `fetch` — the interface stays the same.

---

*Demo project for portfolio purposes. Demo store data is simulated; `books.toscrape.com` is a public sandbox site maintained by Scrapinghub for scraping practice. Only public product pages are accessed, with polite rate limits.*
