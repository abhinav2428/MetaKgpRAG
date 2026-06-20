import sys
import requests
import time
import json
import os
from typing import Generator, Dict, Optional
from config.settings import settings

# Fix Windows cp1252 terminal encoding — wiki page titles contain en-dashes etc.
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_URL = "https://wiki.metakgp.org/api.php"
HEADERS = {"User-Agent": "GraphMind-Bot/1.0 (research project)"}

MAX_RETRIES = 5
RETRY_DELAY = 10         # seconds to wait between retries


def _get_with_retry(params: dict, label: str = "") -> Optional[dict]:
    """
    GET the MediaWiki API with retry on any network/timeout error.
    Returns parsed JSON dict or None after all retries exhausted.
    """
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=60)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            if attempt < MAX_RETRIES:
                print(f"  [RETRY {attempt}/{MAX_RETRIES}] {label}: {e} — waiting {RETRY_DELAY}s")
                time.sleep(RETRY_DELAY)
            else:
                print(f"  [FAILED] {label}: {e} — giving up after {MAX_RETRIES} attempts")
                return None


def get_all_page_titles(limit: int = 500) -> Generator[str, None, None]:
    """
    Fetch ALL page titles via MediaWiki allpages API.
    Paginates automatically with retry on each page of results.
    """
    params = {
        "action": "query",
        "list": "allpages",
        "aplimit": limit,
        "format": "json",
        "apnamespace": 0,   # Main namespace only
    }

    page_num = 0
    while True:
        page_num += 1
        data = _get_with_retry(params, label=f"title-page-{page_num}")
        if data is None:
            print(f"[Scraper] WARNING: Failed to fetch title page {page_num}. Stopping pagination.")
            break

        for page in data["query"]["allpages"]:
            yield page["title"]

        if "continue" not in data:
            break

        params["apcontinue"] = data["continue"]["apcontinue"]
        time.sleep(settings.scrape_delay_seconds)


def get_page_data(title: str) -> Optional[Dict]:
    """
    Fetch full page data for a title with retry on timeout.
    """
    params = {
        "action": "parse",
        "page": title,
        "prop": "wikitext|links|categories|text",
        "format": "json",
    }

    data = _get_with_retry(params, label=title)
    if data is None:
        return None

    if "error" in data:
        print(f"  [SKIP] {title}: {data['error'].get('info', 'unknown error')}")
        return None

    parse = data["parse"]
    page_url = f"https://wiki.metakgp.org/wiki/{title.replace(' ', '_')}"

    return {
        "title": parse["title"],
        "url": page_url,
        "wikitext": parse.get("wikitext", {}).get("*", ""),
        "html": parse.get("text", {}).get("*", ""),
        "links": [
            f"https://wiki.metakgp.org/wiki/{lnk['*'].replace(' ', '_')}"
            for lnk in parse.get("links", [])
            if lnk.get("ns") == 0
        ],
        "categories": [
            cat["*"] for cat in parse.get("categories", [])
        ],
    }


def scrape_all(output_dir: str = None) -> int:
    """
    Scrapes ALL pages (no cap) and saves raw JSON files.
    Scrapes as titles stream in — no need to load all titles first.
    Idempotent: skips already-saved pages, safe to re-run.
    Returns total pages on disk when done.
    """
    output_dir = output_dir or settings.raw_data_dir
    os.makedirs(output_dir, exist_ok=True)

    print("[Scraper] Starting — streaming page titles from MediaWiki API...")

    saved = 0
    skipped = 0
    failed = 0
    i = 0

    for title in get_all_page_titles():
        i += 1
        safe = title.replace("/", "_").replace(" ", "_").replace(":", "_")
        out_path = os.path.join(output_dir, f"{safe}.json")

        if os.path.exists(out_path):
            skipped += 1
            if skipped % 200 == 0:
                print(f"  [CACHED] {skipped} skipped... (title #{i}: {title})")
            continue

        print(f"  [#{i}] Scraping: {title}")
        page_data = get_page_data(title)

        if page_data:
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(page_data, f, ensure_ascii=False, indent=2)
            saved += 1
        else:
            failed += 1

        time.sleep(settings.scrape_delay_seconds)

    total = saved + skipped
    print(f"\n[Scraper] Done. New: {saved} | Cached: {skipped} | Failed: {failed} | Total on disk: {total}")
    return total