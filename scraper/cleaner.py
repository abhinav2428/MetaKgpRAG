import re
import json
import os
from pathlib import Path
from typing import Dict
from bs4 import BeautifulSoup
from config.settings import settings

try:
    import mwparserfromhell
    HAS_MWP = True
except ImportError:
    HAS_MWP = False


def clean_wikitext(wikitext: str) -> str:
    """
    Strip wiki markup and return plain text using mwparserfromhell.
    Falls back to regex-based stripping if library unavailable.
    """
    if not wikitext:
        return ""

    if HAS_MWP:
        wikicode = mwparserfromhell.parse(wikitext)
        text = wikicode.strip_code(normalize=True, collapse=True)
    else:
        # Basic fallback: strip [[links]], {{templates}}, markup
        text = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", wikitext)
        text = re.sub(r"\{\{[^}]*\}\}", "", text)
        text = re.sub(r"=+(.+?)=+", r"\1", text)
        text = re.sub(r"'''?(.+?)'''?", r"\1", text)
        text = re.sub(r"\[https?://\S+ ([^\]]+)\]", r"\1", text)
        text = re.sub(r"\[https?://\S+\]", "", text)

    # Collapse excess whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r" {2,}", " ", text)
    return text.strip()


def clean_html(html: str) -> str:
    """
    Strip HTML and return plain text using BeautifulSoup.
    Used as fallback when wikitext is empty.
    """
    if not html:
        return ""

    soup = BeautifulSoup(html, "html.parser")

    # Remove navigation, editing artifacts, footers
    for tag in soup.find_all(
        ["script", "style", "nav", "footer", "noscript"]
    ):
        tag.decompose()

    for cls in ["mw-editsection", "printfooter", "catlinks", "toc"]:
        for el in soup.find_all(class_=cls):
            el.decompose()

    text = soup.get_text(separator="\n", strip=True)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def clean_page(raw: Dict) -> Dict:
    """
    Clean a single raw page dict. Prefers wikitext; falls back to HTML.
    """
    wikitext = raw.get("wikitext", "")
    html = raw.get("html", "")

    text = clean_wikitext(wikitext) if wikitext else clean_html(html)

    # Skip pages with almost no content (redirects, stubs)
    if len(text) < 80:
        return None

    return {
        "title": raw["title"],
        "url": raw["url"],
        "text": text,
        "links": raw.get("links", []),
        "categories": raw.get("categories", []),
    }


def clean_all(
    raw_dir: str = None,
    clean_dir: str = None,
) -> int:
    raw_dir = raw_dir or settings.raw_data_dir
    clean_dir = clean_dir or settings.clean_data_dir
    os.makedirs(clean_dir, exist_ok=True)

    files = list(Path(raw_dir).glob("*.json"))
    print(f"[Cleaner] Processing {len(files)} raw pages...")

    saved = 0
    for filepath in files:
        with open(filepath, encoding="utf-8") as f:
            raw = json.load(f)

        cleaned = clean_page(raw)
        if cleaned is None:
            print(f"  [SKIP] {raw.get('title', filepath.stem)} — too short")
            continue

        out_path = Path(clean_dir) / filepath.name
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(cleaned, f, ensure_ascii=False, indent=2)

        saved += 1

    print(f"[Cleaner] Done. {saved} pages cleaned.")
    return saved