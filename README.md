## 📌 Problem Statement

Enterprise Customer Data Platforms (CDPs) like Adobe Experience Platform (AEP) and mParticle power modern data architecture, but their developer documentation is vast, highly technical, and fragmented across disparate portals. 

Engineers and architects regularly face steep learning curves and high context-switching costs when attempting to:
- Design and validate compliant data models (e.g., AEP's Experience Data Model / XDM).
- Implement identity resolution, profile merging, and segmentation rules.
- Navigate complex data governance, consent management, and privacy enforcement policies.

### 💡 The Solution

The **Enterprise CDP Architecture Assistant** is a domain-specific Retrieval-Augmented Generation (RAG) system built to serve as an intelligent, conversational knowledge engine over official CDP documentation (AEP & mParticle).

By vectorizing and indexing specialized technical docs on **Segmentation, Unified Profiles, XDM Schemas, and Data Governance**, the system provides:

- **Instant Schema & Policy Verification:** High-precision, source-attributed answers for XDM standards, identity rules, and governance labels in plain English.
- **Hallucination-Free Technical Guidance:** Grounded retrieval ensuring code snippets, API structures, and platform guardrails reflect official vendor specifications.
- **Accelerated Implementation:** Reduced search time for data engineers and martech architects building or maintaining CDP pipelines.


### Architecture diagram
### Key design decisions
##### Parent-child chunking - CDP documentations often constitute of sections and sub-sections, chunking them semantically might not garner the result that we are expecting. Experimentation and solution approaches captured in -.
##### Hybrid search - semantic search only could return close to or similar meaning sections from the documentation, in the context of a CDP, this could dilute the meaning and semantic resulting in unwanted response. 
##### Semantic Cache - With respect to CDP documentation, a lot of queries tend to be repetitive and we can use it to create a semantic cache. This helps in both reducing multiple calls to the LLM, reducing cost and reduces the overall token as well. 
##### Eval results — RAGAS scores, latency numbers - To Do. 


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
