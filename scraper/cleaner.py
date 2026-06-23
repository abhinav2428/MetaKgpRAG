"""
scraper/cleaner.py
------------------
Converts raw MediaWiki page dicts (from data/raw/) into clean plain-text dicts
ready for chunking and embedding.

Rules:
  - Prefers wikitext over HTML.
  - Extracts infobox template fields as readable prose (professor, hall, course).
  - Strips all remaining wiki markup, HTML tags, ref blocks, parser comments.
  - Falls back to HTML cleaning if wikitext yields too little text.
  - Returns None for pages with < MIN_TEXT_LEN chars (redirects, bare stubs).
"""

import re
from typing import Dict, Optional
from bs4 import BeautifulSoup

try:
    import mwparserfromhell
    HAS_MWP = True
except ImportError:
    HAS_MWP = False

MIN_TEXT_LEN = 80   # characters — below this the page is too thin to index


# ---------------------------------------------------------------------------
# Infobox extraction
# ---------------------------------------------------------------------------

def _param_text(param) -> str:
    """Get plain text from a mwparserfromhell template parameter value."""
    val = mwparserfromhell.parse(str(param.value))
    return val.strip_code(normalize=True).strip()


def _extract_infobox_prose(template) -> str:
    """
    Convert an infobox template into readable key: value lines.
    Handles Professor, Hall, and generic infoboxes.
    """
    name = str(template.name).strip().lower()
    lines = []

    params: Dict[str, str] = {}
    for p in template.params:
        key = str(p.name).strip().lower().replace(' ', '_')
        val = _param_text(p) if HAS_MWP else str(p.value).strip()
        if val and val not in ('', '-', 'n/a', 'none'):
            params[key] = val

    if 'professor' in name:
        label_map = [
            ('department', 'Department'),
            ('research_areas', 'Research Areas'),
            ('year_joined', 'Year Joined'),
            ('email', 'Email'),
            ('website', 'Website'),
        ]
        for key, label in label_map:
            if key in params:
                lines.append(f"{label}: {params[key]}")

    elif 'hall' in name:
        label_map = [
            ('name', 'Hall Name'),
            ('founded', 'Founded'),
            ('motto', 'Motto'),
            ('warden', 'Warden'),
            ('capacity', 'Capacity'),
            ('gender', 'Gender'),
            ('sharing', 'Room Types'),
            ('canteen', 'Canteen'),
            ('shops', 'Shops'),
            ('office_no', 'Office Number'),
        ]
        for key, label in label_map:
            if key in params:
                lines.append(f"{label}: {params[key]}")

    else:
        # Generic — dump up to 12 fields
        for key, val in list(params.items())[:12]:
            label = key.replace('_', ' ').capitalize()
            lines.append(f"{label}: {val}")

    return '\n'.join(lines)


# ---------------------------------------------------------------------------
# Wikitext cleaning
# ---------------------------------------------------------------------------

def clean_wikitext(wikitext: str) -> str:
    """
    Return plain text from MediaWiki wikitext.
    Extracts infobox fields as prose before stripping templates.
    """
    if not wikitext:
        return ""

    # Strip <ref>...</ref> and self-closing <ref/> before parsing
    wikitext = re.sub(r'<ref[^>]*>.*?</ref>', '', wikitext, flags=re.DOTALL)
    wikitext = re.sub(r'<ref[^/]*/>', '', wikitext)
    # Strip <pre>...</pre> blocks — usually verbatim emails/logs, keep content
    wikitext = re.sub(r'<pre>(.*?)</pre>', r'\1', wikitext, flags=re.DOTALL)
    # Strip <sup> and <sub>
    wikitext = re.sub(r'<su[pb][^>]*>.*?</su[pb]>', '', wikitext, flags=re.DOTALL)
    # Strip all remaining inline HTML tags (<big>, <small>, <br>, <span>, etc.)
    wikitext = re.sub(r'<[a-zA-Z][^>]*>', '', wikitext)
    wikitext = re.sub(r'</[a-zA-Z]+>', '', wikitext)

    if HAS_MWP:
        wikicode = mwparserfromhell.parse(wikitext)
        parts = []

        # Extract infoboxes as prose, then remove them from the tree.
        # Match any template whose name contains 'infobox' (case-insensitive).
        for tmpl in list(wikicode.filter_templates()):
            tmpl_name = str(tmpl.name).strip().lower()
            if 'infobox' in tmpl_name:
                prose = _extract_infobox_prose(tmpl)
                if prose:
                    parts.append(prose)
                try:
                    wikicode.remove(tmpl)
                except ValueError:
                    pass

        # Strip remaining markup
        stripped = wikicode.strip_code(normalize=True, collapse=True).strip()
        if stripped:
            parts.append(stripped)

        text = '\n\n'.join(parts)
    else:
        # Regex fallback (no mwparserfromhell installed)
        text = re.sub(r'\[\[(?:[^|\]]*\|)?([^\]]*)\]\]', r'\1', wikitext)
        text = re.sub(r'\{\{[^}]*\}\}', '', text)
        text = re.sub(r'=+(.+?)=+\n', r'\1\n', text)
        text = re.sub(r"'''?(.+?)'''?", r'\1', text)
        text = re.sub(r'\[https?://\S+ ([^\]]+)\]', r'\1', text)
        text = re.sub(r'\[https?://\S+\]', '', text)

    # Remove leftover image/file syntax that strip_code may leave
    # e.g. "thumb|alt=|Caption" or "File:Foo.jpg|thumb"
    text = re.sub(r'(?i)\b(file|image|thumb|alt)\s*[:=|][^\n]*', '', text)
    # Remove "Category: ..." lines that bleed through
    text = re.sub(r'(?i)^\s*category\s*:.*$', '', text, flags=re.MULTILINE)
    # Remove bare wiki template remnants like "| key = value" lines
    text = re.sub(r'^\s*\|[^\n]{0,100}$', '', text, flags=re.MULTILINE)
    # Remove lines that are only punctuation / noise
    text = re.sub(r'^[\s|{}\[\]]+$', '', text, flags=re.MULTILINE)

    # Collapse excess whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]{2,}', ' ', text)
    return text.strip()


# ---------------------------------------------------------------------------
# HTML cleaning
# ---------------------------------------------------------------------------

def clean_html(html: str) -> str:
    """
    Return plain text from rendered MediaWiki HTML.
    Removes edit-section links, parser cache comments, citation superscripts,
    and TOC metadata.
    """
    if not html:
        return ""

    # Strip HTML comments first (parser cache reports, revision IDs, etc.)
    html = re.sub(r'<!--.*?-->', '', html, flags=re.DOTALL)

    soup = BeautifulSoup(html, 'html.parser')

    # Remove non-content tags
    for tag in soup.find_all(['script', 'style', 'nav', 'footer', 'noscript', 'meta']):
        tag.decompose()

    # Remove MediaWiki UI chrome
    mw_noise_classes = [
        'mw-editsection',      # [edit] links
        'mw-editsection-bracket',
        'mw-editsection-divider',
        'printfooter',
        'catlinks',
        'toc',                 # table of contents
        'reference',           # inline citation superscripts [1]
        'reflist',             # References section list
        'mw-references-wrap',
        'Z3988',               # COinS metadata spans
    ]
    for cls in mw_noise_classes:
        for el in soup.find_all(class_=cls):
            el.decompose()

    # Remove <sup class="reference"> — citation numbers like [1][2]
    for sup in soup.find_all('sup', class_='reference'):
        sup.decompose()

    text = soup.get_text(separator='\n', strip=True)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


# ---------------------------------------------------------------------------
# Page type detection
# ---------------------------------------------------------------------------

def detect_page_type(raw: Dict) -> str:
    """Heuristically classify a MetaKGP wiki page."""
    title = raw.get('title', '')
    cats = [c.lower() for c in raw.get('categories', [])]
    wt = raw.get('wikitext', '')

    if 'Infobox Professor' in wt or 'Infobox_Professor' in wt:
        return 'professor'
    if any(c in cats for c in ['professors', 'faculty']):
        return 'professor'
    if any(c in cats for c in ['halls of residence']):
        return 'hall'
    if any(c in cats for c in ['incidents']):
        return 'incident'
    if any(c in cats for c in ['student societies', 'clubs', 'technology students\' gymkhana']):
        return 'society'
    # Course codes: 2–4 uppercase letters + 5 digits
    if re.match(r'^[A-Z]{2,4}\d{5}', title):
        return 'course'
    return 'general'


# ---------------------------------------------------------------------------
# Main public function
# ---------------------------------------------------------------------------

def clean_page(raw: Dict) -> Optional[Dict]:
    """
    Clean a raw page dict from data/raw/.
    Returns a cleaned dict, or None if the page is too thin to be useful.

    Input keys:  title, url, wikitext, html, links, categories
    Output keys: title, url, text, page_type, links, categories
    """
    wikitext = raw.get('wikitext', '')
    html = raw.get('html', '')

    # Primary: wikitext
    text = clean_wikitext(wikitext) if wikitext else ''

    # Fallback: HTML (when wikitext is missing OR produces too little)
    if len(text) < MIN_TEXT_LEN and html:
        html_text = clean_html(html)
        if len(html_text) > len(text):
            text = html_text

    if len(text) < MIN_TEXT_LEN:
        return None

    return {
        'title': raw['title'],
        'url': raw['url'],
        'text': text,
        'page_type': detect_page_type(raw),
        'links': raw.get('links', []),
        'categories': raw.get('categories', []),
    }