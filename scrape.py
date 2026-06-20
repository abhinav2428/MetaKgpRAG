#!/usr/bin/env python3
"""Run the scraper: fetch all pages from wiki.metakgp.org"""
from scraper.wiki_api import scrape_all

if __name__ == "__main__":
    n = scrape_all()
    print(f"\n✅ Scraping complete. {n} pages saved to data/raw/")
