# GenAI RAG System

> A production-oriented Retrieval-Augmented Generation (RAG) system capable of handling structured and unstructured documents with hybrid retrieval, multi-model LLM reasoning, and automated document ingestion.

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

Deployed on **Render Cloud** using Docker containers. The chatbot interface is served independently from ingestion and indexing, which run via scheduled automation.

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
| Vector database | Persistent Qdrant Cloud integration |
| Hybrid retrieval | Dense embeddings + BM25 lexical retrieval |
| Rank fusion | Reciprocal Rank Fusion (RRF) |
| LLM routing | Dynamic multi-model selection |
| Source attribution | Document provenance shown in UI |
| Containerized deployment | Docker-based reproducible runtime environment |

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
- Documents contain very little digital text
- Pages are fully scanned
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

- Entire page processed through Vision extraction
- Prevents fragmentation of visual and diagrammatic content

### CSV Strategy

- Stored directly in SQLite — no embeddings required for numeric queries
- Vector embeddings used only when semantic interpretation is needed

---

## Retrieval & Ranking Architecture

### Hybrid Retrieval Pipeline

Retrieval combines three signals fused via **Reciprocal Rank Fusion (RRF)**:

```
Dense Embedding Search
        +
  BM25 Lexical Retrieval
        +
Reciprocal Rank Fusion (RRF)
```

This hybrid approach improves recall and ranking stability over dense-only search.

### Embedding Configuration

| Setting | Value |
|---|---|
| Model | `BAAI/bge-small-en-v1.5` |
| Provider | HuggingFace Inference Router |
| Vector Store | Qdrant Cloud |
| Embeddings | Normalized |

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

### Context Selection

- Global Top-K chunk selection with no per-file aggregation
- Rank-aware selection with context size limits
- Prevents single-document dominance
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
| Claude Haiku | Deep reasoning |

Router decisions are cached to reduce repeated routing overhead.

---

## Automation & Persistence

### Google Drive Sync

Documents are ingested directly from a configured Google Drive folder. The pipeline detects new files, updated files, and previously indexed documents — enabling **incremental indexing** with no duplicate processing.

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

**Metadata Backup**

```
SQLite DB
    ↓
Pickle serialization
    ↓
Gzip compression
    ↓
Upload to Google Drive  →  sqlite_latest.pkl.gz
```

**Vector Store Backup**

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
Hybrid Retrieval (Dense + BM25 + RRF)
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
- **Cloud-native** — hosted embeddings, remote vector store, and cloud backups
- **Backup-safe** — full index recovery from Drive artifacts
- **Modular design** — ingestion, retrieval, and serving are independently extensible
- **Fully containerized runtime** — consistent, reproducible environments via Docker

---

## Next Phase

- [ ] FastAPI backend service
- [ ] API gateway for external integrations
