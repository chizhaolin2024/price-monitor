export interface HistoryPoint {
  price: number | null
  checked_at: number
}

export interface Product {
  id: number
  url: string
  store: string
  title: string
  currency: string
  initial_price: number | null
  lowest_price: number | null
  latest_price: number | null
  status: string
  in_stock: boolean
  last_error: string
  last_checked: number | null
  created_at: number
  history: HistoryPoint[]
}

export interface Alert {
  id: number
  product_id: number
  title: string
  old_price: number
  new_price: number
  currency: string
  channels: string
  message: string
  created_at: number
}

export interface Health {
  status: string
  check_interval_seconds: number
  telegram_configured: boolean
  email_configured: boolean
}

export interface CheckResult {
  checked?: number
  errors?: { product_id: number; title: string; error: string }[]
  alerts?: { id: number; title: string; old_price: number; new_price: number; currency: string; channels: string[] }[]
  status?: string
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const resp = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({}))
    throw new Error(body.detail || `Request failed (${resp.status})`)
  }
  return resp.json()
}

export const api = {
  health: () => request<Health>('/api/health'),
  products: () => request<Product[]>('/api/products'),
  alerts: () => request<Alert[]>('/api/alerts'),
  track: (url: string) => request<Product>('/api/products', { method: 'POST', body: JSON.stringify({ url }) }),
  seed: () => request<{ added: number }>('/api/products/seed', { method: 'POST' }),
  remove: (id: number) => request<{ deleted: number }>(`/api/products/${id}`, { method: 'DELETE' }),
  checkNow: () => request<CheckResult>('/api/check', { method: 'POST' }),
}

export const CURRENCY_SYMBOLS: Record<string, string> = {
  USD: '$',
  GBP: '£',
  EUR: '€',
}

export function money(amount: number | null, currency: string): string {
  if (amount === null || amount === undefined) return '—'
  const symbol = CURRENCY_SYMBOLS[currency] || currency + ' '
  return `${symbol}${amount.toFixed(2)}`
}

export function timeAgo(ts: number | null): string {
  if (!ts) return 'never'
  const diff = Date.now() / 1000 - ts
  if (diff < 60) return 'just now'
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
  return `${Math.floor(diff / 86400)}d ago`
}
