"""
ingest.py
---------
Ingestion pipeline entry point.

Reads every JSON from data/raw/, cleans and chunks it,
writes processed output to data/processed/.

Raw data is NEVER modified.
Idempotent: skips already-processed files (safe to re-run).

Usage:
    python ingest.py                  # process everything
    python ingest.py --force          # re-process even cached files
    python ingest.py --sample 20      # process first 20 files (for testing)
    python ingest.py --stats          # show stats for already-processed files
"""

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path

from scraper.cleaner import clean_page
from scraper.chunker import chunk_page, CHUNK_SIZE, CHUNK_OVERLAP

RAW_DIR = Path('data/raw')
PROCESSED_DIR = Path('data/processed')


def ingest_all(force: bool = False, sample: int = None) -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    raw_files = sorted(RAW_DIR.glob('*.json'))
    if sample:
        raw_files = raw_files[:sample]

    total = len(raw_files)
    print(f'[Ingest] {total} raw files found in {RAW_DIR}')
    print(f'         chunk_size={CHUNK_SIZE}  overlap={CHUNK_OVERLAP}')
    print(f'         output -> {PROCESSED_DIR}\n')

    saved = 0
    skipped_cache = 0
    skipped_thin = 0
    type_counts: Counter = Counter()
    chunk_total = 0

    for i, filepath in enumerate(raw_files, 1):
        out_path = PROCESSED_DIR / filepath.name

        if out_path.exists() and not force:
            skipped_cache += 1
            continue

        with open(filepath, encoding='utf-8') as f:
            try:
                raw = json.load(f)
            except json.JSONDecodeError as e:
                print(f'  [WARN] Bad JSON in {filepath.name}: {e}')
                continue

        cleaned = clean_page(raw)
        if cleaned is None:
            skipped_thin += 1
            continue

        chunked = chunk_page(cleaned, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP)

        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(chunked, f, ensure_ascii=False, indent=2)

        saved += 1
        chunk_total += chunked['chunk_count']
        type_counts[chunked['page_type']] += 1

        if saved % 500 == 0 or (sample and saved % 5 == 0):
            print(f'  [{i}/{total}] processed {saved} pages so far...')

    print('\n' + '-' * 50)
    print(f'[Ingest] Complete')
    print(f'  Processed (new):       {saved}')
    print(f'  Skipped (cached):      {skipped_cache}')
    print(f'  Skipped (too thin):    {skipped_thin}')
    print(f'  Total chunks written:  {chunk_total}')
    if saved:
        print(f'  Avg chunks/page:       {chunk_total / saved:.1f}')
    print(f'\n  Page types:')
    for ptype, count in type_counts.most_common():
        print(f'    {ptype:<12} {count}')


def show_stats() -> None:
    files = list(PROCESSED_DIR.glob('*.json'))
    if not files:
        print('[Stats] No processed files found. Run `python ingest.py` first.')
        return

    type_counts: Counter = Counter()
    chunk_counts = []

    for fp in files:
        with open(fp, encoding='utf-8') as f:
            try:
                d = json.load(f)
            except Exception:
                continue
        type_counts[d.get('page_type', '?')] += 1
        chunk_counts.append(d.get('chunk_count', 0))

    total_chunks = sum(chunk_counts)
    print(f'[Stats] {len(files)} processed pages in {PROCESSED_DIR}')
    print(f'        {total_chunks} total chunks')
    print(f'        avg {total_chunks / len(files):.1f} chunks/page')
    print(f'\n  Page types:')
    for ptype, count in type_counts.most_common():
        print(f'    {ptype:<12} {count}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='MetaKGP ingestion pipeline')
    parser.add_argument('--force', action='store_true',
                        help='Re-process even already-cached files')
    parser.add_argument('--sample', type=int, default=None,
                        help='Only process first N files (for quick testing)')
    parser.add_argument('--stats', action='store_true',
                        help='Show stats for already-processed files and exit')
    args = parser.parse_args()

    if args.stats:
        show_stats()
        sys.exit(0)

    ingest_all(force=args.force, sample=args.sample)
