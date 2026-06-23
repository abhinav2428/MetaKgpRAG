"""
scraper/chunker.py
------------------
Splits cleaned page text into overlapping chunks suitable for embedding
and vector retrieval.

## Design rationale (based on MetaKGP dataset analysis)
 
The MetaKGP wiki has a bimodal text-length distribution:
  - 73% course pages:    median 763 chars   -> whole page = 1 chunk
  - 16% professor pages: median 105 chars   -> whole page = 1 chunk  
  - 11% general/halls/societies/incidents:
                         median 1500+ chars  -> actually need chunking
                         top 5% are 10K+ chars (long incident writeups)

### Embedding model constraints
Most sentence-transformer models (all-MiniLM, all-mpnet, BGE, etc.) have a
context window of 256-512 tokens (~1000-2000 chars). Beyond that, text is
silently truncated and retrieval quality degrades.

### Optimal chunk size = 1500 chars
  - Short pages (<1500): kept as a single chunk — no information loss
  - Long pages: 1500 chars ≈ 300-375 tokens — comfortably within embedding
    window, large enough to preserve paragraph-level context, small enough
    for precise retrieval
  - Overlap of 200 chars carries ~1 sentence of context across boundaries

### Page-title prefix
Every chunk gets the page title prepended as context, so an embedding of
chunk #3 of "Azad Hall of Residence" still knows WHAT it's about. This is
critical for disambiguation when retrieving across 3000+ pages.

Strategy: greedy sentence-aware merging with configurable size and overlap.
No external dependencies.
"""

import re
from typing import List, Dict

CHUNK_SIZE = 1500      # target chunk size in characters
CHUNK_OVERLAP = 200    # chars of overlap carried from prev chunk into next
MIN_CHUNK_LEN = 50     # discard chunks shorter than this (noise)


def _split_into_units(text: str, max_unit: int) -> List[str]:
    """
    Split text into atomic retrieval units.
    Priority: double-newline paragraphs > single-newline lines > sentences.
    Each unit is ≤ max_unit chars (oversized ones get sentence-split).
    """
    paragraphs = re.split(r'\n{2,}', text)
    units = []
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        if len(para) <= max_unit:
            units.append(para)
        else:
            # Split oversized paragraph by sentences
            sentences = re.split(r'(?<=[.!?])\s+', para)
            for s in sentences:
                s = s.strip()
                if s:
                    units.append(s)
    return units


def chunk_text(
    text: str,
    title: str = '',
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> List[str]:
    """
    Split `text` into overlapping chunks.

    If the entire text fits in a single chunk, return it as-is (no splitting).
    Otherwise, use greedy paragraph/sentence merging with overlap.

    Each chunk is prefixed with the page title for embedding context.
    """
    if not text.strip():
        return []

    title_prefix = f'{title}\n\n' if title else ''
    prefix_len = len(title_prefix)

    effective_size = chunk_size - prefix_len

    # Short text: single chunk, no splitting needed
    if len(text) <= effective_size:
        return [(title_prefix + text).strip()]

    units = _split_into_units(text, max_unit=effective_size)
    if not units:
        return []

    chunks: List[str] = []
    current = ''

    for unit in units:
        # Hard-split units that are still too large (rare edge case)
        if len(unit) > effective_size:
            if current.strip():
                chunks.append((title_prefix + current).strip())
                current = ''
            step = max(effective_size - overlap, 1)
            for i in range(0, len(unit), step):
                sub = unit[i:i + effective_size]
                if sub.strip():
                    chunks.append((title_prefix + sub).strip())
            continue

        # Try to add this unit to the current accumulator
        candidate = (current + '\n\n' + unit).strip() if current else unit
        if len(candidate) <= effective_size:
            current = candidate
        else:
            # Emit current chunk
            if current.strip():
                chunks.append((title_prefix + current).strip())
            # Start new chunk with overlap context from previous
            if chunks and overlap > 0:
                prev_text = chunks[-1][prefix_len:]  # strip title prefix
                tail = prev_text[-overlap:]
                # Find a clean word boundary in the tail
                space_idx = tail.find(' ')
                if space_idx > 0:
                    tail = tail[space_idx + 1:]
                current = (tail + '\n\n' + unit).strip()
            else:
                current = unit

    if current.strip():
        chunks.append((title_prefix + current).strip())

    return [c for c in chunks if len(c) >= MIN_CHUNK_LEN]


def chunk_page(
    page: Dict,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> Dict:
    """
    Add a `chunks` list to a cleaned page dict.

    Each chunk entry:
        {
          "index": int,
          "text":  str,         # includes title prefix
        }

    The original `text` field is preserved unchanged.
    """
    text = page.get('text', '')
    title = page.get('title', '')
    chunks = chunk_text(text, title=title, chunk_size=chunk_size, overlap=overlap)

    return {
        **page,
        'chunks': [
            {'index': i, 'text': chunk}
            for i, chunk in enumerate(chunks)
        ],
        'chunk_count': len(chunks),
    }
