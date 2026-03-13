# GenAI RAG System

> A production-oriented Retrieval-Augmented Generation (RAG) system capable of handling structured and unstructured documents with hybrid retrieval, multi-model LLM reasoning, automated document ingestion, and advanced retrieval optimization.

---

## Table of Contents

- [Live Deployment](#live-deployment)
- [Overview](#overview)
- [Core Capabilities](#core-capabilities)
- [Supported Document Formats](#supported-document-formats)
- [Vision + OCR Pipeline](#vision--ocr-pipeline)
- [Hybrid Structured + LLM Reasoning](#hybrid-structured--llm-reasoning)
- [Format-Aware Adaptive Chunking](#format-aware-adaptive-chunking)
- [Retrieval & Ranking Architecture](#retrieval--ranking-architecture)
- [LLM Routing Architecture](#llm-routing-architecture)
- [Automation & Persistence](#automation--persistence)
- [Deployment Architecture](#deployment-architecture)
- [High-Level Architecture](#high-level-architecture)
- [Technical Stack](#technical-stack)
- [Running Locally](#running-locally)
- [Docker Deployment](#docker-deployment)
- [Repository Status](#repository-status)
- [System Characteristics](#system-characteristics)
- [Next Phase](#next-phase)

---

## Live Deployment

The chatbot is deployed and accessible here:

**[https://genai-rag-system-docker-github.onrender.com](https://genai-rag-system-docker-github.onrender.com)**

Deployed on **Render Cloud** using Docker containers. The chatbot interface runs independently from document ingestion and indexing, which run through scheduled automation.

---

## Overview

This repository contains an advanced Retrieval-Augmented Generation (RAG) system capable of answering questions grounded in documents stored in Google Drive.

The system supports multiple document types and automatically adapts its ingestion strategy depending on document structure.

**Supported document types:**

- PDF (text-based)
- PDF (scanned)
- Chart-heavy PDFs
- Embedded tables inside PDFs
- DOCX documents
- CSV structured datasets

The architecture separates **document ingestion**, **vector indexing**, and **chatbot inference** into independent layers to ensure stability and fast deployment.

---

## Core Capabilities

| Capability | Description |
|---|---|
| Multi-format ingestion | PDF, DOCX, CSV with format-aware extraction |
| Google Drive synchronization | Automated incremental ingestion |
| Vision OCR | Gemini Vision extraction for scanned and chart-heavy PDFs |
| Adaptive chunking | Format-aware chunking strategies per document type |
| Semantic embeddings | HuggingFace embeddings (`BAAI/bge-small-en-v1.5`) |
| Vector database | Qdrant Cloud persistent storage |
| Hybrid retrieval | Dense embeddings + BM25 lexical retrieval |
| Rank fusion | Reciprocal Rank Fusion (RRF) |
| Query rewriting | LLM-powered query expansion for ambiguous queries |
| Cross-encoder reranking | Semantic relevance reranking |
| LLM routing | Dynamic multi-model selection |
| Source attribution | Document provenance displayed in UI |
| Containerized deployment | Docker reproducible environment |

---

## Supported Document Formats

| Format | Extraction Method | Chunking Strategy | Reasoning |
|---|---|---|---|
| PDF (text) | pdfplumber | Balanced structural chunking | LLM |
| PDF (charts) | Gemini Vision | Page-level extraction | LLM |
| PDF (scanned) | Gemini Vision OCR | Paragraph chunking | LLM |
| PDF tables | pdfplumber table parser | Row-aware contextual chunks | LLM |
| DOCX | python-docx | Paragraph-based chunks | LLM |
| CSV | Pandas | SQLite structured storage | Deterministic |

---

## Vision + OCR Pipeline

The ingestion pipeline automatically detects when visual processing is required.

### Trigger Conditions

Vision extraction is triggered when:

- Pages contain charts or diagrams
- Documents contain minimal digital text
- Pages are scanned images
- Tables appear inside images

### Vision Extraction Workflow

```
PDF Page
    ↓
Image conversion
    ↓
Gemini Vision OCR
    ↓
Structured text reconstruction
    ↓
Chunk generation
```

> Vision processing occurs **only during ingestion**, never during retrieval.

---

## Hybrid Structured + LLM Reasoning

The system separates reasoning strategies for structured and unstructured data.

### Structured CSV Queries

Structured numeric queries bypass LLM reasoning entirely.

```
Query
    ↓
Intent detection
    ↓
Pandas computation
    ↓
LLM natural language explanation
```

**Supported numeric operations:** `max`, `min`, `average`, `sum`, comparisons

This ensures deterministic numeric reasoning and prevents hallucinations.

### Structured PDF Tables

- Row integrity preservation
- Context-aware entity alignment
- Prevention of cross-row contamination
- Accurate numeric comparisons

---

## Format-Aware Adaptive Chunking

Chunking strategy is dynamically selected based on the detected document format.

### PDF Strategy

- Paragraph grouping with larger context windows
- Reduced fragmentation across sections
- Table rows preserved as atomic semantic units

### Chart-Heavy PDFs

Entire pages are processed via **Gemini Vision extraction** to prevent fragmentation of diagrams and visual content.

### CSV Strategy

CSV files are stored directly in **SQLite** — no embeddings required for numeric queries. Vector embeddings are used only when semantic interpretation is needed.

---

## Retrieval & Ranking Architecture

### Query Rewriting Layer

Short or ambiguous queries reduce retrieval accuracy. To improve recall, the system introduces a **query rewriting stage** before hybrid retrieval.

**Workflow:**

```
User Query
    ↓
Initial semantic retrieval (preview)
    ↓
Relevant context chunks
    ↓
LLM Query Rewriting
    ↓
Improved semantic search query
    ↓
Hybrid retrieval pipeline
```

**Example rewrites:**

| Original Query | Rewritten Query |
|---|---|
| certificate | no objection certificate for student at PES University |
| olympic protest | Olympic Games protests and regulations |
| sports coverage | T-20 World Cup 2014 sports coverage analysis |

Benefits include improved recall, better semantic embeddings, and improved BM25 lexical matching.

### Hybrid Retrieval Pipeline

Retrieval combines multiple signals fused via **Reciprocal Rank Fusion (RRF)**:

```
Query Rewriting
    ↓
Dense Embedding Search
        +
  BM25 Lexical Retrieval
    ↓
Reciprocal Rank Fusion (RRF)
    ↓
Cross-Encoder Reranking
    ↓
File Diversity Filtering
    ↓
Final Context Selection
```

This hybrid approach improves recall and ranking stability over dense-only search.

### Embedding Configuration

| Setting | Value |
|---|---|
| Model | `BAAI/bge-small-en-v1.5` |
| Provider | HuggingFace Inference Router |
| Vector Store | Qdrant Cloud |
| Embeddings | Normalized |

### Cross-Encoder Reranking

A cross-encoder model evaluates relevance between the query and each retrieved chunk.

**Model:**

```
cross-encoder/ms-marco-MiniLM-L-6-v2
```

The model scores each `(query, document_chunk)` pair and reorders chunks based on semantic relevance.

**Example:**

| Chunk | Score |
|---|---|
| Olympic protest rule text | 0.91 |
| Random sports paragraph | 0.22 |

### Ranking Enhancements

Additional post-fusion ranking signals improve retrieval quality:

| Signal | Purpose |
|---|---|
| Keyword overlap scoring | Improves query term matching |
| Exact phrase boosting | Prioritizes verbatim matches |
| File name alignment | Boosts likely source documents |
| Numeric token detection | Improves numeric query recall |
| Structured chunk detection | Prioritizes table-extracted chunks |
| Vision chunk priority | Boosts OCR-extracted content |
| Entity density scoring | Ranks information-dense chunks higher |

### Candidate Expansion Strategy

The system retrieves a larger candidate pool before final ranking to increase the probability of retrieving the correct chunk.

```
User requested results: 5
Initial candidate pool: ~40
Final reranked results: Top-K
```

### File Diversity Filtering

To prevent a single document from dominating retrieval:

```
Maximum chunks per file: 2
```

This ensures balanced document coverage and prevents large PDFs from crowding out other sources.

### Context Selection

- Global Top-K chunk selection with no per-file aggregation
- Rank-aware selection with context size limits
- Ensures balanced, diverse context construction

### Source Attribution

Each answer includes the source document used for generation. Source selection uses query-token alignment, chunk-level metadata, and retrieval ranking signals — ensuring the displayed source matches the document actually used for reasoning.

---

## LLM Routing Architecture

The system dynamically selects the best LLM based on query type.

| Model | Use Case |
|---|---|
| `llama-3.3-70b-versatile` (Groq) | General QA |
| GPT-4o Mini | Summarization |
| Claude Haiku | Complex reasoning |

Router decisions are cached to reduce repeated routing overhead.

---

## Automation & Persistence

### Google Drive Sync

Documents are ingested directly from a configured Google Drive folder. The pipeline detects new files, updated files, and previously indexed documents — enabling **incremental indexing with no duplicate processing**.

### Scheduled Ingestion

Ingestion runs via **GitHub Actions** on a daily schedule.

```
Schedule: Daily at 3:00 AM IST
```

Each run performs:

1. Google Drive synchronization
2. Document extraction
3. Chunk generation
4. Embedding generation
5. Qdrant vector store update
6. SQLite metadata update

### Backup Strategy

Two independent backup layers guarantee full index recoverability.

**Metadata Backup:**

```
SQLite DB
    ↓
Pickle serialization
    ↓
Gzip compression
    ↓
Upload to Google Drive  →  sqlite_latest.pkl.gz
```

**Vector Store Backup:**

```
Qdrant Snapshot
    ↓
Compressed archive
    ↓
Google Drive backup
```

### Fast Startup Restoration

Render deployments do **not** run ingestion. On startup:

```
Application start
    ↓
Check SQLite metadata
    ↓
If missing → download sqlite_latest.pkl.gz from Drive
    ↓
Decompress and restore tracker.db
```

This enables instant chatbot boot without re-indexing documents.

---

## Deployment Architecture

The chatbot is deployed on **Render** using Docker containers.

| Task | Render | GitHub Actions |
|---|:---:|:---:|
| Streamlit chatbot UI | Yes | No |
| Retrieval & generation | Yes | No |
| Vector store connection | Yes | No |
| SQLite restoration | Yes | No |
| Docker container runtime | Yes | No |
| Document ingestion | No | Yes |
| Embedding generation | No | Yes |
| Google Drive sync | No | Yes |

This separation enables faster deployments, stable indexing, and reduced compute costs.

---

## High-Level Architecture

```
Google Drive
      │
      ▼
GitHub Actions (Daily Ingestion)
      │
      ▼
Document Extraction
      │
      ▼
Adaptive Chunking
      │
      ▼
Embedding Generation (HuggingFace)
      │
      ▼
Qdrant Cloud (Vector Store)
      │
      ▼
SQLite Metadata Store
      │
      ▼
Drive Backup (SQLite + Qdrant Snapshots)
      │
      ▼
Docker Container (Render)
      │
      ▼
Streamlit Chatbot
      │
      ▼
Query Rewriting
      │
      ▼
Hybrid Retrieval (Dense + BM25 + RRF)
      │
      ▼
Cross-Encoder Reranking
      │
      ▼
LLM Router
      │
      ▼
Groq / GPT-4o Mini / Claude Haiku
```

---

## Technical Stack

| Component | Technology |
|---|---|
| Language | Python |
| PDF Parsing | pdfplumber |
| Vision OCR | Gemini Vision |
| DOCX Parsing | python-docx |
| Structured Processing | Pandas |
| Embeddings | HuggingFace Inference Router |
| Embedding Model | `BAAI/bge-small-en-v1.5` |
| Vector Store | Qdrant Cloud |
| Metadata Storage | SQLite |
| Sparse Retrieval | BM25 |
| Fusion Algorithm | Reciprocal Rank Fusion (RRF) |
| Reranker | Cross-Encoder (`ms-marco-MiniLM-L-6-v2`) |
| LLM Providers | Groq, OpenRouter |
| Router Model | Groq |
| Frontend | Streamlit |
| Containerization | Docker |
| Deployment | Render |
| Scheduler | GitHub Actions |
| Backup Storage | Google Drive |

---

## Running Locally

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Environment Variables

Create a `.env` file in the project root:

```env
GROQ_API_KEY=your_key
OPENROUTER_API_KEY=your_key
HF_API_KEY=your_key
QDRANT_URL=your_cluster_url
QDRANT_API_KEY=your_key
GOOGLE_SERVICE_ACCOUNT_JSON=your_service_account_json
```

### 3. Run Ingestion

```bash
python scripts/run_daily_sync.py
```

### 4. Launch Chatbot

```bash
streamlit run scripts/app.py
```

Open in browser: `http://localhost:8501`

---

## Docker Deployment

### Build the Image

```bash
docker build -t genai-rag-system .
```

### Run the Container

```bash
docker run -p 8501:8501 genai-rag-system
```

Open in browser: `http://localhost:8501`

The container exposes the Streamlit service on port `8501`.

---

## Repository Status

- [x] Multi-format ingestion pipeline (PDF, DOCX, CSV)
- [x] Gemini Vision OCR integration
- [x] Structured PDF table extraction
- [x] Deterministic CSV computation engine
- [x] Hybrid semantic + BM25 retrieval with RRF
- [x] Query rewriting layer
- [x] Cross-encoder reranking
- [x] Advanced ranking signals
- [x] File diversity filtering
- [x] Qdrant Cloud vector storage
- [x] Google Drive ingestion synchronization
- [x] SQLite metadata persistence
- [x] Incremental indexing with no re-processing
- [x] Scheduled GitHub Actions ingestion
- [x] Drive backup for SQLite and Qdrant snapshots
- [x] Fast startup restoration on Render
- [x] Multi-LLM routing
- [x] Source attribution in UI
- [x] Docker containerization
- [x] Render cloud hosting

---

## System Characteristics

- **No document-specific hardcoding** — retrieval is fully data-driven
- **Deterministic structured reasoning** — numeric queries bypass LLM computation
- **Hybrid retrieval** — improves recall and ranking stability over dense-only search
- **Cross-encoder semantic reranking** — improves final chunk ordering
- **Query rewriting** — improves recall for short or ambiguous queries
- **Cloud-native** — hosted embeddings, remote vector store, and cloud backups
- **Backup-safe** — full index recovery from Drive artifacts
- **Modular design** — ingestion, retrieval, and serving are independently extensible
- **Fully containerized runtime** — consistent, reproducible environments via Docker

---

## Next Phase

- [ ] FastAPI backend service
- [ ] API gateway for external integrations
