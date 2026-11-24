import json
import re
import statistics
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

CONFIG_FILE = Path(__file__).parent / "config.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "it-IT,it;q=0.9,en;q=0.8",
}


def load_config():
    with open(CONFIG_FILE, encoding="utf-8") as f:
        return json.load(f)


def extract_price_from_html(html: str) -> float | None:
    soup = BeautifulSoup(html, "html.parser")

    # JSON-LD
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "{}")
            if isinstance(data, list):
                data = data[0] if data else {}
            offers = data.get("offers") or data.get("Offers")
            if isinstance(offers, list) and offers:
                offers = offers[0]
            if isinstance(offers, dict):
                price = offers.get("price") or offers.get("Price")
                if price:
                    return float(str(price).replace(",", "."))
        except Exception:
            continue

    # Meta
    meta = soup.find("meta", {"property": "product:price:amount"}) or soup.find("meta", {"itemprop": "price"})
    if meta and meta.get("content"):
        try:
            return float(meta["content"].replace(",", "."))
        except ValueError:
            pass

    # Regex fallback
    text = soup.get_text(" ", strip=True)
    patterns = [
        r"(\d{1,3}(?:\.\d{3})*,\d{2})\s*€",
        r"€\s*(\d{1,3}(?:\.\d{3})*,\d{2})",
        r"(\d{1,3}(?:,\d{3})*\.\d{2})\s*€",
    ]
    candidates = []
    for pat in patterns:
        for m in re.finditer(pat, text):
            raw = m.group(1).replace(".", "").replace(",", ".")
            try:
                val = float(raw)
                if 50 < val < 25000:
                    candidates.append(val)
            except ValueError:
                continue
    return min(candidates) if candidates else None


def scrape_price(url: str) -> dict:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        price = extract_price_from_html(resp.text)
        return {"url": url, "price": price, "status": "ok" if price else "no_price", "error": None}
    except Exception as e:
        return {"url": url, "price": None, "status": "error", "error": str(e)}


def run_scraper():
    config = load_config()
    results = []
    for category, products in config.get("categories", {}).items():
        for p in products:
            res = scrape_price(p["url"])
            res["name"] = p["name"]
            res["category"] = category
            results.append(res)
    return results
