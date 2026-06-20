#!/usr/bin/env python3
"""Clean raw pages and index them into ChromaDB."""
from scraper.cleaner import clean_all
from scraper.indexer import MetaKGPIndexer

if __name__ == "__main__":
    print("=== Step 1: Cleaning ===")
    clean_all()

    print("\n=== Step 2: Indexing into ChromaDB ===")
    indexer = MetaKGPIndexer()
    indexer.index_all()
    print(f"\n✅ Indexing complete. Stats: {indexer.stats()}")
