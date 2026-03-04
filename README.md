# GenAI RAG System

> A modular, multi-format, hybrid-reasoning Retrieval-Augmented Generation (RAG) system designed for structured precision and reliable document-grounded responses.

---

## Table of Contents

- [Overview](#overview)
- [Core Capabilities](#core-capabilities)
- [Supported Input Formats](#supported-input-formats)
- [Vision + OCR Pipeline](#vision--ocr-pipeline)
- [Hybrid Structured + LLM Reasoning](#hybrid-structured--llm-reasoning)
- [Format-Aware Adaptive Chunking](#format-aware-adaptive-chunking)
- [Retrieval & Ranking Architecture](#retrieval--ranking-architecture)
- [Automation & Persistence Layer](#automation--persistence-layer)
- [Deployment Architecture](#deployment-architecture)
- [High-Level Architecture](#high-level-architecture)
- [Technical Stack](#technical-stack)
- [Running the System](#running-the-system)
- [Repository Status](#repository-status)
- [System Characteristics](#system-characteristics)
- [Next Phase](#next-phase)

---

## Overview

This repository contains an advanced Retrieval-Augmented Generation (RAG) system capable of handling structured and unstructured documents with hybrid reasoning.

**Supported document types:**
- Structured documents (CSV)
- Unstructured documents (PDF, DOCX)
- Scanned PDFs
- Embedded tables inside PDFs
- Chart-heavy research documents

**Core reasoning features:**
- Hybrid semantic + lexical retrieval
- Deterministic structured numeric computation
- Strict context-grounded answer generation
- Automated document synchronization from Google Drive

The system separates responsibilities across document ingestion, vision extraction, embedding generation, vector storage, hybrid retrieval, LLM reasoning, and persistence/backup. The production architecture intentionally **separates ingestion and inference environments** to ensure reliability and fast deployment.

---

## Core Capabilities

### End-to-End RAG Pipeline

| Capability | Description |
|---|---|
| Multi-format ingestion | PDF, DOCX, CSV with format-aware extraction |
| Google Drive sync | Automated incremental document synchronization |
| Vision OCR | Gemini-powered extraction for scanned and chart-heavy PDFs |
| Adaptive chunking | Structured table-aware chunking with dynamic sizing |
| Semantic embeddings | Hosted `BAAI/bge-small-en-v1.5` via HuggingFace Inference Router |
| Vector storage | Persistent Qdrant Cloud integration |
| Hybrid retrieval | Semantic + BM25 lexical retrieval with RRF fusion |
| Deterministic reasoning | CSV computation engine for structured numeric queries |
| Source attribution | Chunk-level provenance tracking in UI |

---

## Supported Input Formats

| Format | Extraction Method | Chunking Strategy | Reasoning Mode |
|---|---|---|---|
| PDF (Text-based) | pdfplumber | Balanced structural chunking | LLM |
| PDF (Chart-heavy) | Gemini Vision | Context-preserving chunking | LLM |
| PDF (Scanned) | Gemini Vision OCR | Balanced paragraph chunking | LLM |
| PDF Tables | pdfplumber table extraction | Row-aware contextual chunking | LLM |
| DOCX | python-docx | Paragraph-based | LLM |
| CSV | Pandas | SQLite structured storage | Deterministic + LLM |

---

## Vision + OCR Pipeline

The system automatically detects when vision-based extraction is required.

### Trigger Conditions

- Chart-heavy pages
- Sparse digital text
- Fully scanned documents
- Embedded graphical elements
- Image-based tables

### Vision Strategy

- Full-page conversion for chart-heavy pages
- Gemini Vision OCR extraction
- Image-based table reconstruction
- Duplicate page hash prevention
- Controlled API usage limits
- Structured normalization of extracted content

> **Note:** Vision processing occurs **only during ingestion**, never during retrieval.

---

## Hybrid Structured + LLM Reasoning

### CSV Deterministic Engine

For structured CSV queries, the system bypasses LLM reasoning for computation:

- Detects numeric intent (`max`, `min`, `avg`, `sum`)
- Identifies numeric columns dynamically
- Uses Pandas for deterministic computation
- LLM used only for natural language explanation

### Structured PDF Tables

- Row integrity preservation
- Context-aware entity alignment
- Prevention of cross-row contamination
- Accurate numeric comparisons

### Benefits

- Deterministic results for structured queries
- Reduced hallucination risk
- Improved numeric reasoning
- Clean separation between deterministic and LLM reasoning

---

## Format-Aware Adaptive Chunking

The ingestion pipeline dynamically selects chunking strategies based on detected format.

### PDF Balanced Strategy

- Larger context windows with reduced fragmentation
- Paragraph grouping
- Table rows preserved as semantic units
- Metadata embedded inside chunks

### Chart-Heavy Strategy

- Entire page processed through Vision extraction
- Prevents fragmented image chunking
- Preserves visual context

### CSV Strategy

- Stored directly in SQLite
- No embeddings required for numeric queries
- Vector retrieval used only when semantic interpretation is needed

---

## Retrieval & Ranking Architecture

### Embedding Configuration

- Model: `BAAI/bge-small-en-v1.5`
- Hosted via HuggingFace Inference Router
- Normalized embeddings
- Persistent Qdrant Cloud vector store

### Hybrid Retrieval Strategy

Retrieval combines three signals fused via **Reciprocal Rank Fusion (RRF)**:

```
Semantic Embedding Search
        +
  BM25 Lexical Retrieval
        +
Reciprocal Rank Fusion (RRF)
```

### Retrieval Enhancements

Additional ranking signals applied post-fusion:

| Signal | Purpose |
|---|---|
| Keyword overlap scoring | Improves term-match relevance |
| Exact phrase boosting | Prioritizes verbatim query matches |
| File name alignment | Boosts chunks from likely source files |
| Numeric reference detection | Improves structured data recall |
| Structured chunk detection | Prioritizes table-extracted chunks |
| Vision content priority | Elevates OCR-extracted content |
| Entity density scoring | Ranks information-dense chunks higher |

### Context Selection

- Global Top-K chunk selection (no per-file aggregation)
- Rank-aware chunk selection
- Context size limits for LLM efficiency
- Prevents single-document dominance in retrieval

### Source Attribution

- Answer-aware chunk detection
- Chunk-level provenance tracking
- UI source links correspond to the actual generating document

---

## Automation & Persistence Layer

### Google Drive Synchronization

Documents are ingested directly from a designated Google Drive folder. The ingestion pipeline:

- Detects new or updated documents
- Performs incremental indexing
- Avoids re-processing previously indexed files

---

### Scheduled Ingestion

Document ingestion runs via **GitHub Actions scheduled workflows**.

```
Schedule: Daily at 3:00 AM IST
```

Each scheduled run performs:

1. Google Drive document synchronization
2. Incremental ingestion of new files
3. Chunk generation
4. Embedding generation
5. Vector storage update in Qdrant Cloud
6. SQLite metadata update

---

### Backup Strategy

Two independent backup mechanisms ensure full recoverability.

#### Metadata Backup

```
SQLite DB
    ↓
Pickle serialization
    ↓
Gzip compression
    ↓
Upload to Google Drive  →  sqlite_latest.pkl.gz
```

#### Vector Store Backup

```
Qdrant Snapshot
    ↓
Compressed Archive
    ↓
Upload to Google Drive
```

---

### Fast Startup Restoration

Render deployments do **not** run ingestion. On startup:

```
Startup
    ↓
Check if SQLite exists
    ↓
If missing → download sqlite_latest.pkl.gz from Drive
    ↓
Decompress and restore tracker.db
```

This enables instant chatbot boot without re-indexing documents.

---

## Deployment Architecture

The chatbot interface is deployed on **Render**.

### Render Responsibilities

| Responsibility | Render | GitHub Actions |
|---|:---:|:---:|
| Host Streamlit UI | ✅ | ❌ |
| Connect to Qdrant Cloud | ✅ | ❌ |
| Restore SQLite metadata | ✅ | ❌ |
| Execute retrieval + generation | ✅ | ❌ |
| Document ingestion | ❌ | ✅ |
| Embedding generation | ❌ | ✅ |
| Drive synchronization | ❌ | ✅ |

This separation ensures fast startup, stable deployments, no duplicate indexing, and reduced cloud compute usage.

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
Render — Streamlit App
      │
      ▼
Hybrid Retrieval (Dense + BM25 + RRF)
      │
      ▼
Groq Llama 3.3 (Answer Generation)
```

---

## Technical Stack

| Component | Technology |
|---|---|
| Language | Python |
| PDF Extraction | pdfplumber |
| Vision OCR | Gemini 2.5 Flash Vision |
| DOCX Parsing | python-docx |
| Structured Data | Pandas |
| Embeddings | HuggingFace Inference Router |
| Embedding Model | `BAAI/bge-small-en-v1.5` |
| Vector Store | Qdrant Cloud |
| Metadata Store | SQLite |
| Sparse Retrieval | BM25 |
| Fusion Algorithm | Reciprocal Rank Fusion (RRF) |
| LLM Backend | Groq |
| Primary Model | `llama-3.3-70b-versatile` |
| Fallback Model | `llama-3.1-8b-instant` |
| Scheduler | GitHub Actions |
| Backup Storage | Google Drive |
| Frontend | Streamlit |
| Deployment | Render |

---

## Running the System

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Environment Variables

Create a `.env` file in the project root:

```env
GROQ_API_KEY=your_key
HF_API_KEY=your_key
QDRANT_URL=your_cluster_url
QDRANT_API_KEY=your_key
GOOGLE_SERVICE_ACCOUNT_JSON=your_service_account_json
```

### 3. Run Ingestion Locally

```bash
python scripts/run_daily_sync.py
```

### 4. Launch Chatbot

```bash
streamlit run scripts/app.py
```

Open in browser:

```
http://localhost:8501
```

---

## Repository Status

The current implementation is stable and includes:

- [x] Multi-format ingestion pipeline (PDF, DOCX, CSV)
- [x] Gemini Vision OCR integration
- [x] Structured PDF table extraction
- [x] Deterministic CSV computation engine
- [x] Hybrid semantic + BM25 retrieval with RRF
- [x] Qdrant Cloud vector storage
- [x] Google Drive ingestion synchronization
- [x] SQLite metadata persistence
- [x] Incremental ingestion (no re-processing)
- [x] Scheduled GitHub Actions indexing
- [x] Drive backup for SQLite + Qdrant snapshots
- [x] Fast startup restoration on Render
- [x] Streamlit UI deployed on Render

---

## System Characteristics

- **No document-specific hardcoding** — retrieval is fully data-driven
- **Deterministic numeric reasoning** — structured queries bypass LLM computation
- **Hybrid retrieval** — improves recall and ranking stability over dense-only search
- **Cloud-native** — hosted embeddings, remote vector store, and cloud backups
- **Backup-safe** — full index recovery from Drive artifacts
- **Modular design** — ingestion, retrieval, and serving are independently extensible

---

## Next Phase

Planned improvements for the next development cycle:

- [ ] FastAPI backend architecture
- [ ] Docker containerization
- [ ] Multi-user authentication
- [ ] Observability and metrics
- [ ] Retrieval evaluation tooling
