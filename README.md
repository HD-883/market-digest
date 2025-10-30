# Market Digest — v4 (Options Playbook)
Adds a lightweight **Options Playbook (educational)** driven by weekly trends.

## What’s included
- Plain-English headline & bottom line
- 💹 Watchlist (momentum heuristic)
- 🧰 **Options Playbook** with defined-risk ideas:
  - **Up** trend → Call calendar or Bull Call Debit Spread
  - **Down** trend → Put calendar or Bear Put Debit Spread
  - **Sideways** → Iron Condor (7–14DTE)
- Metals get macro clauses (real yields & dollar).

## Sources
- Yahoo Finance (CSV): prices for ^GSPC, DX-Y.NYB, BTC-USD, ETH-USD, XAUUSD=X, XAGUSD=X, plus large-cap tickers.
- FRED: DFII10 (10y TIPS real yield).

## Setup
Replace in your repo:
- `index.html`, `styles.css`
- `scripts/update.py`
- `.github/workflows/update.yml`

Publish via **Settings → Pages → Deploy from branch → main / (root)**.

⚠️ Educational only. Options carry significant risk and can result in total loss of premium.
_Last generated: 2025-10-30_
