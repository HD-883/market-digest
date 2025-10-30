#!/usr/bin/env python3
# v4 updater: adds "options_playbook" suggestions based on verdict trends.
# Strategies are defined‑risk and heuristic: call/put debit spreads, calendars, condors.

import os, sys, json, time, math, csv, io, urllib.parse, datetime
import urllib.request
from statistics import mean

def y_download(symbol, days=200):
    end = int(time.time())
    start = end - days*24*3600
    base = "https://query1.finance.yahoo.com/v7/finance/download/"
    url = f"{base}{urllib.parse.quote(symbol)}?period1={start}&period2={end}&interval=1d&events=history&includeAdjustedClose=true"
    with urllib.request.urlopen(url, timeout=30) as resp:
        data = resp.read().decode("utf-8")
    rows = list(csv.DictReader(io.StringIO(data)))
    rows = [r for r in rows if r.get("Close") not in (None, "", "null")]
    return rows

def fred_csv(series):
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}"
    with urllib.request.urlopen(url, timeout=30) as resp:
        data = resp.read().decode("utf-8")
    rows = list(csv.DictReader(io.StringIO(data)))
    rows = [r for r in rows if r.get(series) not in (None, "", ".", "NaN")]
    return rows

def pct_change(a, b):
    if b == 0 or b is None or a is None: return None
    return (a - b) / b * 100.0

def pick_last_and_week(rows, col="Close"):
    if not rows: return None, None
    try: last = float(rows[-1][col])
    except: last = None
    week_idx = max(0, len(rows) - 7)
    try: week = float(rows[week_idx][col])
    except: week = None
    return last, week

def sma(vals, n):
    if len(vals) < n: return None
    return mean(vals[-n:])

def get_close_series(rows, col="Close"):
    vals = []
    for r in rows:
        try: vals.append(float(r[col]))
        except: pass
    return vals

symbols = {
    "SPX": "^GSPC",
    "DXY": "DX-Y.NYB",
    "BTC": "BTC-USD",
    "ETH": "ETH-USD",
    "XAU": "XAUUSD=X",
    "XAG": "XAGUSD=X",
}

universe = ["AAPL","MSFT","NVDA","AMZN","GOOGL","META","TSLA","AVGO","NFLX","COST","AMD","CRM","ADBE","INTC","ORCL","JPM","BAC","GS","UNH","LLY","XOM","CVX","WMT","HD","CAT","PEP","KO","V","MA","PG","NKE","MCD","GE","BA","NOW","PANW","MU","SMCI"]

data = {}

for k,s in symbols.items():
    try:
        rows = y_download(s, days=90)
        last, week = pick_last_and_week(rows, "Close")
        data[k] = {"last": last, "week": week, "rows": len(rows)}
    except Exception as e:
        data[k] = {"error": str(e)}

try:
    fred_rows = fred_csv("DFII10")
    last_val = float(fred_rows[-1]["DFII10"])
    last_date = datetime.datetime.strptime(fred_rows[-1]["DATE"], "%Y-%m-%d").date()
    target = last_date - datetime.timedelta(days=7)
    prev_val = None
    for r in reversed(fred_rows[:-1]):
        d = datetime.datetime.strptime(r["DATE"], "%Y-%m-%d").date()
        if d <= target and r["DFII10"] not in ("", ".", "NaN"):
            prev_val = float(r["DFII10"])
            break
    data["REAL_YIELD"] = {"last": last_val, "week": prev_val}
except Exception as e:
    data["REAL_YIELD"] = {"error": str(e)}

def wchg(key):
    if key not in data or "last" not in data[key] or data[key]["last"] is None or data[key]["week"] is None:
        return None
    return pct_change(data[key]["last"], data[key]["week"])

changes = {k: wchg(k) for k in ["SPX","DXY","BTC","ETH","XAU","XAG"]}

gsr = None
if data.get("XAU", {}).get("last") and data.get("XAG", {}).get("last"):
    try: gsr = data["XAU"]["last"] / data["XAG"]["last"]
    except: gsr = None

ryd = None
if data.get("REAL_YIELD", {}).get("last") is not None and data["REAL_YIELD"].get("week") is not None:
    ryd = (data["REAL_YIELD"]["last"] - data["REAL_YIELD"]["week"]) * 100.0

def verdict_from_change(ch, up_th, down_th=None):
    if ch is None: return "Sideways"
    if down_th is None: down_th = -up_th
    if ch >= up_th: return "Up"
    if ch <= down_th: return "Down"
    return "Sideways"

verdicts = []
vmap = [
    ("Stocks", changes["SPX"], 1.0, "S&P 500 weekly move"),
    ("BTC", changes["BTC"], 3.0, "BTC weekly move"),
    ("ETH", changes["ETH"], 4.0, "ETH weekly move"),
    ("Gold", changes["XAU"], 1.0, "Gold weekly move"),
    ("Silver", changes["XAG"], 2.0, "Silver weekly move"),
]
for asset, ch, th, note in vmap:
    trend = verdict_from_change(ch, up_th=th)
    nnote = f"{note}: {ch:.2f}%." if ch is not None else f"{note}: n/a."
    verdicts.append({"asset": asset, "trend": trend, "note": nnote})

macro = []
macro.append(f"10y TIPS real yield Δ: {ryd:.0f} bps w/w." if ryd is not None else "10y TIPS real yield Δ: n/a.")
macro.append(f"DXY weekly change: {changes['DXY']:.2f}%." if changes["DXY"] is not None else "DXY weekly change: n/a.")

metals = []
if changes["XAU"] is not None and data["XAU"].get("last"):
    metals.append(f"Gold: {data['XAU']['last']:.2f} ({changes['XAU']:.2f}% w/w).")
if changes["XAG"] is not None and data["XAG"].get("last"):
    metals.append(f"Silver: {data['XAG']['last']:.2f} ({changes['XAG']:.2f}% w/w).")
if gsr is not None:
    metals.append(f"Gold/Silver Ratio (GSR): {gsr:.1f}.")

equities = []
if changes["SPX"] is not None and data["SPX"].get("last"):
    equities.append(f"S&P 500: {data['SPX']['last']:.2f} ({changes['SPX']:.2f}% w/w).")

crypto = []
for k, name in [("BTC","BTC"),("ETH","ETH")]:
    if changes[k] is not None and data[k].get("last"):
        crypto.append(f"{name}: {data[k]['last']:.2f} ({changes[k]:.2f}% w/w).")

alerts = []
if ryd is not None and abs(ryd) >= 25: alerts.append(f"ALERT: Real yield moved {ryd:.0f} bps w/w — rate backdrop shifting.")
if changes["DXY"] is not None and abs(changes["DXY"]) >= 1.5: alerts.append(f"ALERT: DXY {changes['DXY']:.2f}% w/w — dollar swing impacts risk & metals.")
if changes["SPX"] is not None and abs(changes["SPX"]) >= 3.0: alerts.append(f"ALERT: S&P 500 {changes['SPX']:.2f}% w/w — equity regime change risk.")
if changes["BTC"] is not None and abs(changes["BTC"]) >= 10.0: alerts.append(f"ALERT: BTC {changes['BTC']:.2f}% w/w — volatility spike.")
if changes["ETH"] is not None and abs(changes["ETH"]) >= 12.0: alerts.append(f"ALERT: ETH {changes['ETH']:.2f}% w/w — volatility spike.")
if gsr is not None and (gsr < 75 or gsr > 90): alerts.append(f"ALERT: GSR at {gsr:.1f} — silver vs gold regime signal.")
for k, nm, thr in [("XAU","Gold",5.0),("XAG","Silver",5.0)]:
    if changes[k] is not None and abs(changes[k]) >= thr: alerts.append(f"ALERT: {nm} {changes[k]:.2f}% w/w — large weekly move.")
if not alerts: alerts = ["No alert triggered this run."]

# Watchlist
def y_sma_ok(tkr):
    try:
        rows = y_download(tkr, days=160)
        if len(rows) < 60: return None
        last, week = pick_last_and_week(rows, "Close")
        series = get_close_series(rows, "Close")
        sma20 = sma(series, 20)
        sma50 = sma(series, 50)
        ch = pct_change(last, week) if (last is not None and week is not None) else None
        if None in (last, week, sma20, sma50, ch): return None
        if (last > sma20) and (last > sma50) and (sma20 > sma50) and (ch > 0):
            return {"ticker": tkr, "wk_change_pct": round(ch,2)}
    except: return None
    return None

watchlist = []
for tkr in universe:
    rec = y_sma_ok(tkr)
    if rec:
        rec["reason"] = f"It might be a good time to buy {tkr}: price above 20/50DMA, +{rec['wk_change_pct']:.1f}% this week."
        watchlist.append(rec)
watchlist.sort(key=lambda x: x["wk_change_pct"], reverse=True)
watchlist = watchlist[:12]

# Options playbook (heuristic, defined‑risk)
# Map assets to liquid option proxies where applicable
proxies = {
    "Stocks": "SPY",   # proxy for S&P 500
    "Gold": "GLD",
    "Silver": "SLV",
    "BTC": "BITO",     # ETF proxy; crypto venue options differ
    "ETH": "ETHO"      # placeholder; many brokers don't offer ETH options ETF; user discretion
}

def option_idea(asset, trend, ch, ryd, dxy_ch):
    t = (trend or "Sideways").lower()
    proxy = proxies.get(asset, asset)
    base = {"ticker": proxy, "strategy": "", "text": ""}
    # Volatility heuristic from abs weekly %
    vol = abs(ch) if ch is not None else 0.0
    # Choose spread width and DTE
    width = "2–5" if proxy not in ("SPY","GLD","SLV") else "5–10"
    dte = "30–45 DTE"

    if t == "up":
        if vol < 2.0:
            base["strategy"] = "Call calendar"
            base["text"] = f"Buy {proxy} {dte} ATM call, sell 7–14DTE call; aims to benefit from steady uptrend."
        else:
            base["strategy"] = "Bull call debit spread"
            base["text"] = f"Buy 1 {proxy} {dte} ATM call, sell 1 +{width} OTM call; defined risk if trend continues."
    elif t == "down":
        if vol < 2.0:
            base["strategy"] = "Put calendar"
            base["text"] = f"Buy {proxy} {dte} ATM put, sell 7–14DTE put; benefits from gradual drift lower."
        else:
            base["strategy"] = "Bear put debit spread"
            base["text"] = f"Buy 1 {proxy} {dte} ATM put, sell 1 -{width} OTM put; defined risk for downside."
    else:
        base["strategy"] = "Iron condor"
        base["text"] = f"Sell 7–14DTE iron condor around current price; keep it small and manage early."

    # Add a short macro clause for GLD/SLV
    if asset in ("Gold","Silver"):
        if ryd is not None and ryd < 0:
            base["text"] += " Tailwind: real yields softer."
        if dxy_ch is not None and dxy_ch < 0:
            base["text"] += " Dollar easing helps metals."
    return base

options_playbook = []
trend_map = {v["asset"]: v["trend"] for v in verdicts}
chg_map = {"Stocks": changes["SPX"], "BTC": changes["BTC"], "ETH": changes["ETH"], "Gold": changes["XAU"], "Silver": changes["XAG"]}

for asset in ["Stocks","Gold","Silver","BTC","ETH"]:
    options_playbook.append(option_idea(asset, trend_map.get(asset), chg_map.get(asset), ryd, changes["DXY"]))

# Also add up to top 5 watchlist tickers with generic bullish spread idea
for w in watchlist[:5]:
    options_playbook.append({
        "ticker": w["ticker"],
        "strategy": "Bull call debit spread",
        "text": f"Trend up on weekly basis; consider {w['ticker']} { '30–45 DTE' } call spread; cap risk, aim to ride momentum."
    })

events = [
    "Watch: CPI/PCE, Jobs (NFP), ISM/PMI, central-bank minutes.",
    "Earnings: megacaps, semis, money-center banks when due."
]

out = {
  "last_updated": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
  "verdicts": verdicts,
  "macro": macro,
  "equities": equities,
  "crypto": crypto,
  "metals": metals,
  "events": events,
  "alerts": alerts,
  "watchlist": watchlist,
  "options_playbook": options_playbook
}

with open("data.json","w",encoding="utf-8") as f:
    json.dump(out, f, indent=2)

print("Updated data.json")
