#!/usr/bin/env python3
# v5 updater: freshness + provenance + robust fetch
# - Retries with backoff + UA header
# - Records as-of dates for Yahoo & FRED
# - Emits 'freshness' and 'provenance' fields

import os, sys, json, time, math, csv, io, urllib.parse, datetime, random
import urllib.request
from statistics import mean

UA = "Mozilla/5.0 (compatible; MarketDigestBot/1.0; +https://example.com)"
def fetch(url, retries=3, timeout=30):
    err = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except Exception as e:
            err = e
            time.sleep(1.5 * (i+1) + random.random())
    raise err

def y_download(symbol, days=200):
    end = int(time.time())
    start = end - days*24*3600
    base = "https://query1.finance.yahoo.com/v7/finance/download/"
    url = f"{base}{urllib.parse.quote(symbol)}?period1={start}&period2={end}&interval=1d&events=history&includeAdjustedClose=true"
    data = fetch(url).decode("utf-8")
    rows = list(csv.DictReader(io.StringIO(data)))
    rows = [r for r in rows if r.get("Close") not in (None, "", "null")]
    return rows

def fred_csv(series):
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}"
    data = fetch(url).decode("utf-8")
    rows = list(csv.DictReader(io.StringIO(data)))
    rows = [r for r in rows if r.get(series) not in (None, "", ".", "NaN")]
    return rows

def pct_change(a, b):
    if b == 0 or b is None or a is None: return None
    return (a - b) / b * 100.0

def pick_last_and_week(rows, col="Close"):
    if not rows: return None, None, None
    try: last = float(rows[-1][col])
    except: last = None
    week_idx = max(0, len(rows) - 7)
    try: week = float(rows[week_idx][col])
    except: week = None
    asof = rows[-1].get("Date") or rows[-1].get("DATE") or ""
    return last, week, asof

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
provenance = []
yf_asof_list = []

for k,s in symbols.items():
    try:
        rows = y_download(s, days=90)
        last, week, asof = pick_last_and_week(rows, "Close")
        data[k] = {"last": last, "week": week, "rows": len(rows)}
        provenance.append({"symbol": k, "source": "Yahoo Finance CSV", "asof": asof})
        if asof: yf_asof_list.append(asof)
    except Exception as e:
        data[k] = {"error": str(e)}

fred_asof = None
try:
    fred_rows = fred_csv("DFII10")
    last_val = float(fred_rows[-1]["DFII10"])
    fred_asof = fred_rows[-1]["DATE"]
    last_date = datetime.datetime.strptime(fred_asof, "%Y-%m-%d").date()
    target = last_date - datetime.timedelta(days=7)
    prev_val = None
    for r in reversed(fred_rows[:-1]):
        d = datetime.datetime.strptime(r["DATE"], "%Y-%m-%d").date()
        if d <= target and r["DFII10"] not in ("", ".", "NaN"):
            prev_val = float(r["DFII10"])
            break
    data["REAL_YIELD"] = {"last": last_val, "week": prev_val}
    provenance.append({"symbol": "REAL_YIELD", "source": "FRED DFII10", "asof": fred_asof})
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

def sma_ok_record(tkr):
    try:
        rows = y_download(tkr, days=160)
        if len(rows) < 60: return None
        last, week, asof = pick_last_and_week(rows, "Close")
        series = get_close_series(rows, "Close")
        sma20 = sma(series, 20)
        sma50 = sma(series, 50)
        ch = pct_change(last, week) if (last is not None and week is not None) else None
        if None in (last, week, sma20, sma50, ch): return None
        if (last > sma20) and (last > sma50) and (sma20 > sma50) and (ch > 0):
            return {"ticker": tkr, "wk_change_pct": round(ch,2), "asof": asof}
    except: return None
    return None

watchlist = []
for tkr in universe:
    rec = sma_ok_record(tkr)
    if rec:
        rec["reason"] = f"It might be a good time to buy {tkr}: price above 20/50DMA, +{rec['wk_change_pct']:.1f}% this week."
        watchlist.append(rec)
watchlist.sort(key=lambda x: x["wk_change_pct"], reverse=True)
watchlist = watchlist[:12]

provenance += [{"symbol": f"WATCHLIST:{w['ticker']}", "source": "Yahoo Finance CSV", "asof": w["asof"]} for w in watchlist]

# Options playbook (same as v4)
proxies = {"Stocks":"SPY","Gold":"GLD","Silver":"SLV","BTC":"BITO","ETH":"ETHO"}
def option_idea(asset, trend, ch, ryd, dxy_ch):
    t = (trend or "Sideways").lower()
    proxy = proxies.get(asset, asset)
    base = {"ticker": proxy, "strategy": "", "text": ""}
    vol = abs(ch) if ch is not None else 0.0
    width = "2–5" if proxy not in ("SPY","GLD","SLV") else "5–10"
    dte = "30–45 DTE"
    if t == "up":
        if vol < 2.0:
            base["strategy"] = "Call calendar"
            base["text"] = f"Buy {proxy} {dte} ATM call, sell 7–14DTE call; steady uptrend idea."
        else:
            base["strategy"] = "Bull call debit spread"
            base["text"] = f"Buy 1 {proxy} {dte} ATM call, sell 1 +{width} OTM call; defined risk."
    elif t == "down":
        if vol < 2.0:
            base["strategy"] = "Put calendar"
            base["text"] = f"Buy {proxy} {dte} ATM put, sell 7–14DTE put; drift‑down idea."
        else:
            base["strategy"] = "Bear put debit spread"
            base["text"] = f"Buy 1 {proxy} {dte} ATM put, sell 1 -{width} OTM put; defined risk."
    else:
        base["strategy"] = "Iron condor"
        base["text"] = f"Sell 7–14DTE iron condor; manage early; keep size small."
    if asset in ("Gold","Silver"):
        if ryd is not None and ryd < 0: base["text"] += " Tailwind: real yields softer."
        if dxy_ch is not None and dxy_ch < 0: base["text"] += " Dollar easing helps metals."
    return base

trend_map = {}
for v in verdicts:
    trend_map[v["asset"]] = v["trend"]
chg_map = {"Stocks": changes["SPX"], "BTC": changes["BTC"], "ETH": changes["ETH"], "Gold": changes["XAU"], "Silver": changes["XAG"]}
options_playbook = [option_idea(a, trend_map.get(a), chg_map.get(a), (data.get("REAL_YIELD") or {}).get("last") - (data.get("REAL_YIELD") or {}).get("week") if (data.get("REAL_YIELD") or {}).get("week") is not None else None, changes["DXY"]) for a in ["Stocks","Gold","Silver","BTC","ETH"]]
for w in watchlist[:5]:
    options_playbook.append({"ticker": w["ticker"], "strategy": "Bull call debit spread", "text": f"Weekly uptrend; consider {w['ticker']} 30–45 DTE call spread; cap risk; follow momentum."})

# Freshness aggregate
yf_asof = max(yf_asof_list) if yf_asof_list else None

events = ["Watch: CPI/PCE, Jobs (NFP), ISM/PMI, central-bank minutes.", "Earnings: megacaps, semis, banks when due."]

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
  "options_playbook": options_playbook,
  "provenance": provenance,
  "freshness": {"yf_asof": yf_asof, "fred_asof": fred_asof}
}

with open("data.json","w",encoding="utf-8") as f:
    json.dump(out, f, indent=2)

print("Updated data.json")
