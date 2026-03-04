# GenAI RAG System
## Design, Implementation & Architecture Overview

A modular, multi-format, hybrid-reasoning Retrieval-Augmented Generation (RAG) system designed for structured precision and reliable document-grounded responses.

The system supports:

- Multi-format ingestion (PDF, DOCX, CSV)
- Vision-based extraction for scanned and chart-heavy PDFs
- Format-aware adaptive chunking
- Hosted semantic embeddings (HuggingFace Inference Router)
- Hybrid semantic + lexical retrieval
- Deterministic structured computation
- Persistent vector storage with Qdrant Cloud
- Automated Google Drive synchronization and backups
- Production-ready cloud deployment via Render

The architecture is modular, ingestion-safe, production-extensible, and optimized for grounding accuracy.

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

This repository contains an advanced Retrieval-Augmented Generation (RAG) system capable of handling:

- Structured documents (CSV)
- Unstructured documents (PDF, DOCX)
- Scanned PDFs
- Embedded tables inside PDFs
- Chart-heavy research documents
- Hybrid semantic + lexical retrieval
- Deterministic structured numeric computation
- Strict context-grounded answer generation
- Automated document synchronization from Google Drive

The system separates responsibilities between:

- Document ingestion
- Vision extraction
- Embedding generation
- Vector storage
- Hybrid retrieval
- LLM reasoning
- Persistence and backup

The current implementation is stable and deployed for demonstration using Streamlit on Render.

---

## Core Capabilities

### End-to-End RAG Pipeline

- Multi-format document ingestion
- Google Drive ingestion synchronization
- Format-aware extraction logic
- Vision-based OCR for scanned and image-heavy PDFs
- Structured table-aware chunking
- Adaptive chunk sizing
- Hosted semantic embeddings (`BAAI/bge-small-en-v1.5`)
- Persistent vector storage using Qdrant Cloud
- SQLite metadata + structured storage
- Hybrid semantic + lexical retrieval
- BM25 sparse retrieval
- Reciprocal Rank Fusion (RRF)
- Context-aware ranking improvements
- Deterministic CSV computation engine
- Strict document-grounded prompting
- Source attribution in UI

---

## Supported Input Formats

| Format | Extraction Method | Chunking Strategy | Reasoning Mode |
|--------|------------------|-------------------|----------------|
| PDF (Text-based) | pdfplumber | Balanced structural chunking | LLM |
| PDF (Chart-heavy) | Gemini 2.5 Flash Vision | Context-preserving chunking | LLM |
| PDF (Scanned) | Gemini 2.5 Flash Vision OCR | Balanced paragraph chunking | LLM |
| PDF Tables | pdfplumber table extraction | Row-aware contextual chunking | LLM |
| DOCX | python-docx | Paragraph-based | LLM |
| CSV | Pandas | SQLite structured storage | Deterministic + LLM |

---

## Vision + OCR Pipeline

The system detects when vision-based extraction is required.

### Trigger Conditions

- Chart-heavy pages
- Sparse digital text
- Fully scanned documents
- Embedded graphical elements
- Image-based tables

### Vision Strategy

- Full-page conversion for chart-heavy pages
- Gemini 2.5 Flash Vision for OCR extraction
- Image-based table reconstruction
- Duplicate page hash prevention
- Controlled API usage limits
- Structured normalization of extracted content

> Vision processing is used only during document ingestion, not during retrieval.

---

## Hybrid Structured + LLM Reasoning

### CSV Deterministic Engine

For structured CSV queries:

- Detects numeric intent (max, min, avg, sum, count)
- Identifies numeric columns dynamically
- Uses Pandas for deterministic computation
- LLM used only for explanation

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

The ingestion pipeline dynamically selects chunking strategies.

### PDF Balanced Strategy

- Larger context windows
- Reduced fragmentation
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

The system uses:

- Hosted embeddings via HuggingFace Inference Router
- `BAAI/bge-small-en-v1.5`
- Normalized embeddings
- Persistent Qdrant Cloud vector store

### Hybrid Retrieval Strategy

Retrieval combines multiple signals:

- Semantic embedding search
- BM25 lexical retrieval
- Reciprocal Rank Fusion (RRF)

This ensures robustness for both semantic and keyword-based queries.

### Retrieval Enhancements

Additional ranking signals include:

- Keyword overlap scoring
- Exact phrase boosting
- File name alignment
- Numeric reference detection
- Structured chunk detection
- Vision content priority
- Entity density scoring

### Context Selection Improvements

To improve retrieval reliability:

- Global Top-K chunk selection
- Removal of file-level score aggregation
- Rank-aware chunk selection
- Context size limits to maintain LLM efficiency

This prevents dominance of documents with many chunks.

### Source Attribution

Source attribution uses:

- Answer-aware chunk detection
- Chunk-level provenance tracking

This ensures that UI source links correspond to the actual document used to generate the answer.

---

## Automation & Persistence Layer

### Google Drive Synchronization

The system supports automated ingestion from Google Drive. Documents can be synced periodically to ensure the vector index stays up-to-date.

### Backup Strategy

Two independent backup mechanisms are implemented:

**Metadata Backup**
- SQLite → Pickle serialization → Google Drive
- Ensures that structured metadata can be restored

**Vector Store Backup**
- Qdrant → Snapshot → Google Drive
- Vector index snapshots are periodically stored in Drive for recovery

### Rehydration

On restart, the system can restore metadata, vector database state, and document indexing from backup artifacts.

---

## Deployment Architecture

The application is deployed using Render.

**Deployment characteristics:**

- Python environment
- Streamlit application
- Qdrant Cloud remote vector database
- Hosted embedding inference
- Groq LLM API

**Render provides:**

- Automatic deployment from GitHub
- Containerized environment
- Public endpoint for chatbot interface

The deployment uses a lightweight configuration suitable for prototype and demonstration environments.

---

## High-Level Architecture

```
Google Drive / Local Documents
          │
   Controlled Ingestion Pipeline
          │
   Format-Aware Extraction
          │
 Gemini Vision Layer (OCR + Tables)
          │
 Adaptive Chunking
          │
 HuggingFace Hosted Embeddings
          │
 Qdrant Cloud (Vector Store)
          │
 SQLite Metadata Store
          │
 Hybrid Retrieval
 (Semantic + BM25 + RRF)
          │
 Context Selection
 (Global Top-K Chunks)
          │
 Groq Llama 3.3
          │
 Streamlit Interface (Render)
```

---

## Technical Stack

| Component | Technology |
|-----------|------------|
| Language | Python |
| PDF Extraction | pdfplumber |
| Vision OCR | Gemini 2.5 Flash |
| DOCX Parsing | python-docx |
| Structured Data | Pandas |
| Embeddings | HuggingFace Inference Router |
| Embedding Model | `BAAI/bge-small-en-v1.5` |
| Vector Store | Qdrant Cloud |
| Metadata Store | SQLite |
| Sparse Retrieval | BM25 |
| Fusion Algorithm | Reciprocal Rank Fusion |
| LLM Backend | Groq |
| Primary Model | `llama-3.3-70b-versatile` |
| Fallback Model | `llama-3.1-8b-instant` |
| Scheduler | APScheduler |
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

Create a `.env` file:

```
GROQ_API_KEY=your_key
GEMINI_API_KEY=your_key
HF_API_KEY=your_key
QDRANT_URL=your_cluster_url
QDRANT_API_KEY=your_key
```

### 3. Run Ingestion

```bash
python -m src.ingestion.main
```

### 4. Launch UI

```bash
streamlit run scripts/app.py
```

Open in browser:

```
http://localhost:8501
```

---

## Repository Status

Stable implementation currently includes:

- Multi-format ingestion pipeline
- Gemini Vision OCR integration
- Structured PDF table extraction
- Deterministic CSV computation
- Hybrid semantic + lexical retrieval
- BM25 + RRF ranking
- Qdrant Cloud vector storage
- Google Drive ingestion synchronization
- SQLite metadata persistence
- Qdrant snapshot backup
- Automated backup workflows
- Streamlit UI deployment on Render

---

## System Characteristics

- No document-specific hardcoding
- Retrieval fully data-driven
- Deterministic numeric reasoning
- Hybrid retrieval improves recall and ranking stability
- Cloud-hosted embeddings
- Remote vector storage
- Backup-safe architecture
- Modular design supporting future scaling

---

## Next Phase

Future development goals include:

- FastAPI backend architecture
- Docker containerization
- Scalable multi-instance deployment
- Observability and monitoring
