# Market Digest — Auto Site
Mobile-first, auto-updating site for Stocks, BTC, ETH, Gold & Silver.

## One-time setup
1. Create a **public** GitHub repo, e.g. `market-digest`.
2. Upload all files in this ZIP preserving folders (`scripts/`, `.github/workflows/`).
3. Enable **Pages**: Settings → Pages → Source: **Deploy from branch**, Branch: `main`, Folder: **/(root)**.
4. Allow **Actions**: Settings → Actions → General → Allow all actions.
5. Within ~1 cycle, your site will be live at: `https://<your-username>.github.io/market-digest/`  
   Example: `https://ali-weekly.github.io/market-digest/`

## Data sources (no API keys)
- Yahoo Finance CSV downloads: ^GSPC, DX-Y.NYB, BTC-USD, ETH-USD, XAUUSD=X, XAGUSD=X
- FRED fredgraph.csv: DFII10 (10y TIPS real yield)

## Alerts (shown on site)
- Real yield ±25 bps w/w; DXY ±1.5% w/w; S&P ±3% w/w; BTC ±10% w/w; ETH ±12% w/w; GSR <75 or >90; Gold/Silver ±5% w/w.

## Customize
- Edit thresholds or add assets in `scripts/update.py`.
- Change schedule in `.github/workflows/update.yml` (cron).

_Last generated: 2025-10-30_
