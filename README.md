# Market Digest — v5 (Provenance & Freshness)
- Adds **data provenance** (source + as-of date for each symbol)
- Adds **freshness** line on the site (Yahoo EOD date + FRED date)
- Robust fetching (headers, retries, backoff)
- Increases schedule to **every 3 hours**

**Sources**
- Prices: Yahoo Finance CSV (EOD daily data; FX/metals as provided by Yahoo)
- Real yields: FRED DFII10 (Federal Reserve Bank of St. Louis)

**Notes**
- EOD = End-of-day; for intraday prices, change the updater to use intraday endpoints or broker APIs.
- Educational only; not financial advice.
