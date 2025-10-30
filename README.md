# Market Digest — v3 (Plain-English + Watchlist)
Mobile-first, auto-updating site with a simple watchlist powered by price momentum.

## What’s new
- **Plain-English headline & bottom line.**
- **💹 This Week’s Watchlist:** auto-built from large-cap tickers when:
  - Price > 20-day SMA
  - Price > 50-day SMA
  - 20-day SMA > 50-day SMA
  - 1-week change > 0%
  → Each entry says: “It might be a good time to buy TICKER …” (non-advisory).

## Data sources
- Yahoo Finance CSV: ^GSPC, DX-Y.NYB, BTC-USD, ETH-USD, XAUUSD=X, XAGUSD=X, and a basket of large caps (AAPL, MSFT, NVDA, AMZN, …).
- FRED: DFII10 (10-year TIPS real yield).

## Setup (replace files)
1) Upload/replace: `index.html`, `styles.css`, `scripts/update.py`, `.github/workflows/update.yml` (keep same schedule or adjust).
2) Ensure **Settings → Pages** is set to **Deploy from branch**, **main / (root)**.

## Notes
- All text is educational and not financial advice.
- The watchlist is a heuristic screen — not a guarantee of performance.

_Last generated: 2025-10-30_
