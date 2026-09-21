"""
small-to-big chunker for DCDP Rag assistant

Strategy: Small-to-big (aka Parent-child chunking)
- small chunks(256 tokens) used for precise retrieval. 
- Each small chunk is linked to its parent large chunk(512 tokens)
- Parent chunk sent to LLM for generation (more context)
- child chunk used for embedding./retrieval (more precise)


Alternative consideredL Fixed-size chunking
 - Rejected after experiementing : splits mis-sentence , losses heading context
 - would hurt retrieval precision on technical terminology. 

"""

import json