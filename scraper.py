import json
import re
from typing import Optional

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "it-IT,it;q=0.9,pl;q=0.8,en;q=0.7",
}


def extract_price_from_html(html: str) -> Optional[float]:
    soup = BeautifulSoup(html, "html.parser")

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

    meta = soup.find("meta", {"property": "product:price:amount"}) or soup.find("meta", {"itemprop": "price"})
    if meta and meta.get("content"):
        try:
            return float(meta["content"].replace(",", "."))
        except ValueError:
            pass

    text = soup.get_text(" ", strip=True)
    patterns = [
        r"(\d{1,3}(?:\.\d{3})*,\d{2})\s*[€zł]",
        r"[€zł]\s*(\d{1,3}(?:\.\d{3})*,\d{2})",
        r"(\d{1,3}(?:,\d{3})*\.\d{2})\s*[€zł]",
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


def search_marketplace(query: str, site: str, lang: str = "it") -> list:
    results = []
    try:
        if lang == "pl":
            if site == "allegro":
                search_url = f"https://allegro.pl/listing?string={requests.utils.quote(query)}"
            else:
                search_url = f"https://www.ceneo.pl/;szukaj-{requests.utils.quote(query)}"
        else:
            if site == "trovaprezzi":
                search_url = f"https://www.trovaprezzi.it/arredamento-ufficio/offerte/{query.replace(' ', '-')}"
            else:
                search_url = f"https://www.idealo.it/risultati.html?q={requests.utils.quote(query)}"

        resp = requests.get(search_url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            for a in soup.find_all("a", href=True)[:8]:
                if "http" in a["href"] or a["href"].startswith("/"):
                    price = extract_price_from_html(str(a))
                    if price:
                        href = a["href"] if a["href"].startswith("http") else search_url
                        results.append({
                            "name": a.get_text(strip=True)[:60] or query,
                            "url": href,
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


def search_google_shopping(query: str, lang: str = "it") -> list:
    results = []
    try:
        hl = "pl" if lang == "pl" else "it"
        gl = "pl" if lang == "pl" else "it"
        search_url = f"https://www.google.com/search?tbm=shop&q={requests.utils.quote(query)}&hl={hl}&gl={gl}"
        resp = requests.get(search_url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            for div in soup.find_all(["div", "span", "a"])[:20]:
                text = div.get_text(" ", strip=True)
                price = extract_price_from_html(str(div))
                if price:
                    link = div.find("a") if div.name != "a" else div
                    href = link.get("href", "") if link else ""
                    if href.startswith("/url?q="):
                        href = href.split("&")[0].replace("/url?q=", "")
                    results.append({
                        "name": text[:60] or query,
                        "url": href or search_url,
                        "price": price,
                        "source": "Google Shopping",
                        "status": "ok",
                        "error": None,
                    })
                    if len(results) >= 3:
                        break
    except Exception:
        pass
    return results


def search_amazon(query: str, lang: str = "it") -> list:
    results = []
    try:
        domain = "amazon.pl" if lang == "pl" else "amazon.it"
        search_url = f"https://www.{domain}/s?k={requests.utils.quote(query)}"
        resp = requests.get(search_url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            for item in soup.select(".s-result-item")[:6]:
                title_el = item.select_one("h2 a span") or item.select_one(".a-text-normal")
                price_el = item.select_one(".a-price .a-offscreen") or item.select_one(".a-price-whole")
                link_el = item.select_one("h2 a")
                if title_el and price_el:
                    price_text = price_el.get_text(strip=True)
                    price = extract_price_from_html(f"<span>{price_text}</span>")
                    if price:
                        href = f"https://www.{domain}" + link_el["href"] if link_el and link_el.get("href") else search_url
                        results.append({
                            "name": title_el.get_text(strip=True)[:60],
                            "url": href,
                            "price": price,
                            "source": "Amazon",
                            "status": "ok",
                            "error": None,
                        })
                        if len(results) >= 3:
                            break
    except Exception:
        pass
    return results


def analyze(product_url: str, competitor_urls: list[str], product_keywords: str = None, lang: str = "it") -> list[dict]:
    results = []

    main = scrape_price(product_url, "Tuo prodotto" if lang == "it" else "Twój produkt")
    results.append(main)

    for i, url in enumerate(competitor_urls, 1):
        if url.strip():
            label = f"Concorrente {i}" if lang == "it" else f"Konkurent {i}"
            results.append(scrape_price(url.strip(), label))

    query = product_keywords or main.get("name", "scrivania" if lang == "it" else "biurko")
    if query:
        if lang == "pl":
            results.extend(search_marketplace(query, "allegro", lang))
            results.extend(search_marketplace(query, "ceneo", lang))
        else:
            results.extend(search_marketplace(query, "trovaprezzi", lang))
            results.extend(search_marketplace(query, "idealo", lang))
        results.extend(search_google_shopping(query, lang))
        results.extend(search_amazon(query, lang))

    return results
