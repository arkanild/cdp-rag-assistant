"""
Parent-Child Chunker for CDP RAG Assistant

Strategy (based on notebook experiments on AEP + mParticle docs):
- Split each doc on real '## ' headings (scraper-inserted)
- Strip preamble before the first heading (mParticle nav noise)
- Parent  = one section (capped at PARENT_MAX chars, split at sentence ends)
- Child   = ~600 char windows of a parent, with overlap, heading prepended
- Children are embedded and retrieved; parents are fetched for generation

Design notes:
- IDs are deterministic hashes, so re-running is idempotent
  (the embedder skips IDs already in ChromaDB).
- Char offsets are relative to the section body, not the whole document.
"""

import json
import re
import hashlib
import logging
from pathlib import Path
from dataclasses import dataclass, asdict, field
from typing import Optional

logger = logging.getLogger(__name__)

# ── Constants (chars; ~4 chars per token) ─────────────────────────────────────
CHARS_PER_TOKEN = 4
PARENT_MAX = 2400        # ~600 tokens
CHILD_SIZE = 600         # ~150 tokens
CHILD_OVERLAP = 100      # ~25 tokens
MIN_BODY = 40            # skip near-empty sections

HEADING_RE = re.compile(r"(?m)^## (.+)$")

def make_id(*parts) -> str:
    """deterministic ID: same input always gives the same ID."""
    raw = ":".join(str(p) for p in parts)
    return hashlib.sha1(raw.encode()).hexdigest()[:20]


