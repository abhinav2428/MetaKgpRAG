"""Quick analysis script for chunk size optimization."""
import json, os
from pathlib import Path
from collections import Counter

processed_dir = Path('data/processed')
files = sorted(processed_dir.glob('*.json'))

text_lens = []
chunk_lens = []
chunks_per_page = []
type_text_lens = {}

for f in files:
    with open(f, encoding='utf-8') as fh:
        d = json.load(fh)
    tl = len(d['text'])
    text_lens.append(tl)
    pt = d.get('page_type', 'unknown')
    type_text_lens.setdefault(pt, []).append(tl)
    chunks_per_page.append(d['chunk_count'])
    for c in d.get('chunks', []):
        chunk_lens.append(len(c['text']))

text_lens.sort()
chunk_lens.sort()

def percentile(arr, p):
    idx = int(len(arr) * p / 100)
    return arr[min(idx, len(arr)-1)]

print('=== TEXT LENGTH DISTRIBUTION (chars) ===')
print(f'  Total pages:  {len(text_lens)}')
print(f'  Min:          {text_lens[0]}')
print(f'  P10:          {percentile(text_lens, 10)}')
print(f'  P25:          {percentile(text_lens, 25)}')
print(f'  Median:       {percentile(text_lens, 50)}')
print(f'  P75:          {percentile(text_lens, 75)}')
print(f'  P90:          {percentile(text_lens, 90)}')
print(f'  P95:          {percentile(text_lens, 95)}')
print(f'  Max:          {text_lens[-1]}')

print()
print('=== TEXT LENGTH BY PAGE TYPE ===')
for pt in sorted(type_text_lens.keys()):
    lens = sorted(type_text_lens[pt])
    n = len(lens)
    print(f'  {pt:<12} n={n:>4}  median={percentile(lens, 50):>6}  p75={percentile(lens, 75):>6}  p95={percentile(lens, 95):>6}  max={lens[-1]:>6}')

print()
print('=== CHUNK LENGTH DISTRIBUTION (chars) ===')
print(f'  Total chunks: {len(chunk_lens)}')
print(f'  Min:          {chunk_lens[0]}')
print(f'  P10:          {percentile(chunk_lens, 10)}')
print(f'  P25:          {percentile(chunk_lens, 25)}')
print(f'  Median:       {percentile(chunk_lens, 50)}')
print(f'  P75:          {percentile(chunk_lens, 75)}')
print(f'  P90:          {percentile(chunk_lens, 90)}')
print(f'  Max:          {chunk_lens[-1]}')

print()
print('=== CHUNKS PER PAGE DISTRIBUTION ===')
cpg = Counter(chunks_per_page)
for k in sorted(cpg.keys())[:15]:
    bar = '#' * min(cpg[k] // 5, 60)
    print(f'  {k:>2} chunks: {cpg[k]:>5} pages  {bar}')
if max(cpg.keys()) > 15:
    rest = sum(v for k, v in cpg.items() if k > 15)
    print(f'  16+ chunks: {rest:>4} pages')

single = sum(1 for c in chunks_per_page if c == 1)
print(f'\n  Single-chunk pages: {single}/{len(chunks_per_page)} ({100*single/len(chunks_per_page):.0f}%)')
