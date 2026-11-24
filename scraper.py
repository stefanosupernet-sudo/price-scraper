import json
import re
from typing import Optional

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "it-IT,it;q=0.9,en;q=0.8",
}


def extract_price_from_html(html: str) -> Optional[float]:
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

    # Regex
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


def extract_title(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    title = soup.find("title")
    if title:
        return title.get_text(strip=True).split("|")[0].split("-")[0].strip()
    h1 = soup.find("h1")
    return h1.get_text(strip=True) if h1 else "Prodotto"


def scrape_price(url: str, name: str = None) -> dict:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        price = extract_price_from_html(resp.text)
        title = extract_title(resp.text) if not name else name
        return {
            "name": title[:80],
            "url": url,
            "price": price,
            "source": "Diretto",
            "status": "ok" if price else "no_price",
            "error": None,
        }
    except Exception as e:
        return {
            "name": name or url,
            "url": url,
            "price": None,
            "source": "Diretto",
            "status": "error",
            "error": str(e),
        }


def search_marketplace(query: str, site: str = "trovaprezzi") -> list:
    """Best-effort search on Trovaprezzi or Idealo. Often blocked by anti-bot."""
    results = []
    try:
        if site == "trovaprezzi":
            search_url = f"https://www.trovaprezzi.it/arredamento-ufficio/offerte/{query.replace(' ', '-')}"
        else:  # idealo
            search_url = f"https://www.idealo.it/risultati.html?q={requests.utils.quote(query)}"
        resp = requests.get(search_url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            for a in soup.find_all("a", href=True)[:8]:
                if "http" in a["href"] and any(x in a["href"] for x in ["product", "offerta", "item"]):
                    price = extract_price_from_html(str(a))
                    if price:
                        results.append({
                            "name": a.get_text(strip=True)[:60] or query,
                            "url": a["href"],
                            "price": price,
                            "source": site.capitalize(),
                            "status": "ok",
                            "error": None,
                        })
                        if len(results) >= 3:
                            break
    except Exception:
        pass
    return results


def analyze(product_url: str, competitor_urls: list[str], product_keywords: str = None) -> list[dict]:
    results = []

    # Scrape main product
    main = scrape_price(product_url, "Tuo prodotto")
    results.append(main)

    # Competitors
    for i, url in enumerate(competitor_urls, 1):
        if url.strip():
            results.append(scrape_price(url.strip(), f"Concorrente {i}"))

    # Lookalikes from marketplaces
    query = product_keywords or main.get("name", "scrivania classica")
    if query:
        results.extend(search_marketplace(query, "trovaprezzi"))
        results.extend(search_marketplace(query, "idealo"))

    return results
