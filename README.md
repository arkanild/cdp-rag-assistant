Problem statement — why CDP documentation is hard to query
Architecture diagram — the flow we designed
Key design decisions — why hybrid search, why small-to-big chunking, why semantic cache
Eval results — RAGAS scores, latency numbers
What I'd do differently — shows reflectionß


High level Architecture 

User Query
    ↓
Query Embedding (Vertex AI text-embedding-004)
    ↓
Semantic Cache Check (Redis) → Cache Hit → Return cached answer
    ↓ Cache Miss
Hybrid Retrieval
├── Dense: Vertex AI Matching Engine
└── Sparse: BM25 on document index
    ↓
Reciprocal Rank Fusion
    ↓
Cross-encoder Re-ranking (top 5 chunks)
    ↓
Staleness Check (chunk metadata)
    ↓
LLM Generation (Gemini Pro via Vertex AI)
    ↓
RAGAS Eval (async, logged to BigQuery)
    ↓
Response + Staleness Warning (if applicable)
    ↓
Cache Store (Redis)