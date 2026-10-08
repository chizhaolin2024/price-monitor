import { useCallback, useEffect, useMemo, useState } from 'react'
import { api, money, timeAgo, type Alert, type Health, type Product } from './api'

function Sparkline({ product }: { product: Product }) {
  const points = useMemo(() => {
    const prices = product.history.filter((h) => h.price !== null).map((h) => h.price as number)
    if (prices.length < 2) return null
    const width = 220
    const height = 48
    const min = Math.min(...prices)
    const max = Math.max(...prices)
    const range = max - min || 1
    return prices
      .map((price, i) => {
        const x = (i / (prices.length - 1)) * width
        const y = height - 4 - ((price - min) / range) * (height - 10)
        return `${x.toFixed(1)},${y.toFixed(1)}`
      })
      .join(' ')
  }, [product])

  if (!points) {
    return <div className="sparkline-placeholder">Awaiting first price checks…</div>
  }
  const trending = product.latest_price !== null && product.initial_price !== null && product.latest_price < product.initial_price
  return (
    <svg className="sparkline" width="220" height="48" viewBox="0 0 220 48">
      <polyline points={points} fill="none" stroke={trending ? '#16a34a' : '#64748b'} strokeWidth="2" strokeLinejoin="round" />
    </svg>
  )
}

function ProductCard({ product, onRemove }: { product: Product; onRemove: (id: number) => void }) {
  const dropFromInitial =
    product.latest_price !== null && product.initial_price !== null && product.latest_price < product.initial_price
      ? ((product.initial_price - product.latest_price) / product.initial_price) * 100
      : null
  const atLowest =
    product.latest_price !== null && product.lowest_price !== null && product.latest_price <= product.lowest_price + 0.009

  return (
    <div className={`card product-card ${product.status === 'error' ? 'card-error' : ''}`}>
      <div className="product-head">
        <span className="store-badge">{product.store}</span>
        <button className="icon-btn" title="Stop tracking" onClick={() => onRemove(product.id)}>
          ×
        </button>
      </div>
      <a className="product-title" href={product.url.startsWith('demo://') ? undefined : product.url} target="_blank" rel="noreferrer">
        {product.title}
      </a>
      {product.status === 'error' ? (
        <div className="error-text">Check failed: {product.last_error || 'unknown error'}</div>
      ) : (
        <>
          <div className="price-row">
            <span className="price-current">{money(product.latest_price, product.currency)}</span>
            {dropFromInitial !== null && dropFromInitial > 0.05 && (
              <span className="badge badge-drop">▼ {dropFromInitial.toFixed(1)}% since tracking</span>
            )}
            {atLowest && product.history.length > 1 && <span className="badge badge-lowest">lowest yet</span>}
          </div>
          <Sparkline product={product} />
          <div className="product-meta">
            <span>Tracked at {money(product.initial_price, product.currency)}</span>
            <span>Lowest {money(product.lowest_price, product.currency)}</span>
            <span>Checked {timeAgo(product.last_checked)}</span>
          </div>
        </>
      )}
    </div>
  )
}

function AlertRow({ alert }: { alert: Alert }) {
  const pct = ((alert.old_price - alert.new_price) / alert.old_price) * 100
  return (
    <div className="alert-row">
      <div className="alert-main">
        <span className="alert-title">{alert.title}</span>
        <span className="alert-prices">
          {money(alert.old_price, alert.currency)} → <strong>{money(alert.new_price, alert.currency)}</strong>
          <span className="badge badge-drop">-{pct.toFixed(1)}%</span>
        </span>
      </div>
      <div className="alert-meta">
        {alert.channels.split(',').map((c) => (
          <span key={c} className="channel-badge">
            {c}
          </span>
        ))}
        <span>{timeAgo(alert.created_at)}</span>
      </div>
    </div>
  )
}

export default function App() {
  const [health, setHealth] = useState<Health | null>(null)
  const [products, setProducts] = useState<Product[]>([])
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [url, setUrl] = useState('')
  const [busy, setBusy] = useState(false)
  const [checking, setChecking] = useState(false)
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')

  const refresh = useCallback(async () => {
    const [productList, alertList] = await Promise.all([api.products(), api.alerts()])
    setProducts(productList)
    setAlerts(alertList)
  }, [])

  useEffect(() => {
    api.health().then(setHealth).catch(() => undefined)
    refresh().catch(() => undefined)
    const timer = setInterval(() => refresh().catch(() => undefined), 30000)
    return () => clearInterval(timer)
  }, [refresh])

  const flash = (message: string, isError = false) => {
    if (isError) setError(message)
    else setNotice(message)
    setTimeout(() => {
      setNotice('')
      setError('')
    }, 6000)
  }

  const handleTrack = async () => {
    if (!url.trim()) return
    setBusy(true)
    setError('')
    try {
      await api.track(url.trim())
      setUrl('')
      await refresh()
      flash('Product is now being tracked.')
    } catch (err) {
      flash(err instanceof Error ? err.message : 'Failed to track product', true)
    } finally {
      setBusy(false)
    }
  }

  const handleSeed = async () => {
    setBusy(true)
    try {
      const result = await api.seed()
      await refresh()
      flash(`Loaded ${result.added} demo products into your watchlist.`)
    } catch (err) {
      flash(err instanceof Error ? err.message : 'Failed to load demo products', true)
    } finally {
      setBusy(false)
    }
  }

  const handleCheck = async () => {
    setChecking(true)
    setError('')
    try {
      const result = await api.checkNow()
      if (result.status === 'already_running') {
        flash('A check is already running.')
      } else {
        await refresh()
        const parts = [`Checked ${result.checked ?? 0} products`]
        if (result.alerts?.length) parts.push(`${result.alerts.length} price drop alert${result.alerts.length > 1 ? 's' : ''} sent`)
        if (result.errors?.length) parts.push(`${result.errors.length} error${result.errors.length > 1 ? 's' : ''}`)
        flash(parts.join(' · '))
      }
    } catch (err) {
      flash(err instanceof Error ? err.message : 'Check failed', true)
    } finally {
      setChecking(false)
    }
  }

  const handleRemove = async (id: number) => {
    await api.remove(id)
    await refresh()
  }

  return (
    <div className="page">
      <header className="header">
        <div>
          <h1>PriceWatch</h1>
          <p className="subtitle">Track product prices across stores — get pinged the moment they drop.</p>
        </div>
        <div className="status-pills">
          <span className={`pill ${health?.telegram_configured ? 'pill-on' : 'pill-off'}`}>
            Telegram {health?.telegram_configured ? 'on' : 'off'}
          </span>
          <span className={`pill ${health?.email_configured ? 'pill-on' : 'pill-off'}`}>
            Email {health?.email_configured ? 'on' : 'off'}
          </span>
          <span className="pill pill-info">
            auto-check every{' '}
            {health
              ? health.check_interval_seconds >= 3600
                ? `${Math.round(health.check_interval_seconds / 3600)}h`
                : `${Math.round(health.check_interval_seconds / 60)}m`
              : '1h'}
          </span>
        </div>
      </header>

      <section className="card controls">
        <div className="track-form">
          <input
            type="text"
            value={url}
            placeholder="Paste a product URL to track (demo://headphones or a books.toscrape.com product page)"
            onChange={(e) => setUrl(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleTrack()}
          />
          <button className="btn btn-primary" onClick={handleTrack} disabled={busy || !url.trim()}>
            {busy ? 'Working…' : 'Track product'}
          </button>
        </div>
        <div className="control-row">
          <button className="btn btn-ghost" onClick={handleSeed} disabled={busy}>
            Load 3 demo products
          </button>
          <button className="btn btn-accent" onClick={handleCheck} disabled={checking}>
            {checking ? 'Checking prices…' : '⟳ Check prices now'}
          </button>
        </div>
        {notice && <div className="banner banner-ok">{notice}</div>}
        {error && <div className="banner banner-err">{error}</div>}
      </section>

      <section className="stats-row">
        <div className="stat">
          <span className="stat-value">{products.length}</span>
          <span className="stat-label">products tracked</span>
        </div>
        <div className="stat">
          <span className="stat-value">{alerts.length}</span>
          <span className="stat-label">price drop alerts</span>
        </div>
        <div className="stat">
          <span className="stat-value">
            {products.filter((p) => p.status === 'error').length}
          </span>
          <span className="stat-label">stores failing</span>
        </div>
      </section>

      <div className="grid">
        <section>
          <h2>Watchlist</h2>
          {products.length === 0 ? (
            <div className="card empty-state">
              Nothing tracked yet. Load the demo products or paste a product URL above.
            </div>
          ) : (
            <div className="product-list">
              {products.map((product) => (
                <ProductCard key={product.id} product={product} onRemove={handleRemove} />
              ))}
            </div>
          )}
        </section>

        <aside>
          <h2>Alerts</h2>
          <div className="card alerts-panel">
            {alerts.length === 0 ? (
              <div className="empty-state small">No drops yet. Run a few checks — or wait for the hourly run.</div>
            ) : (
              alerts.map((alert) => <AlertRow key={alert.id} alert={alert} />)
            )}
          </div>
        </aside>
      </div>

      <footer className="footer">
        Per-store parsers · SQLite price history · Telegram + email alerts · runs unattended on a schedule
      </footer>
    </div>
  )
}
