# GenAI RAG System
## Design, Implementation & Architecture Overview

A modular, multi-format, hybrid-reasoning **Retrieval-Augmented Generation (RAG)** system designed for structured precision and reliable document-grounded responses.

The system supports:

- Multi-format ingestion (PDF, DOCX, CSV)
- Vision-based extraction for scanned and chart-heavy PDFs
- Format-aware adaptive chunking
- Lightweight semantic embeddings
- Deterministic structured computation
- Hybrid retrieval and structural re-ranking
- Automated persistence and synchronization

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

The system separates responsibilities cleanly between:

- Vision extraction
- Embedding layer
- Deterministic numeric reasoning
- LLM-based semantic reasoning
- Automated persistence and backup

The current implementation is **stable and demo-ready via Streamlit**.

---

## Core Capabilities

### End-to-End RAG Pipeline

- Multi-format document ingestion
- Format-aware extraction logic
- Vision-based OCR for scanned and image-heavy PDFs
- Structured table-aware chunking
- Adaptive chunk sizing
- Lightweight semantic embeddings (`bge-small-en-v1.5`)
- Persistent vector storage (ChromaDB)
- SQLite metadata + structured storage
- Hybrid semantic + lexical retrieval
- Structural re-ranking boosts
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

- Chart-heavy pages (multiple raster images)
- Sparse digital text
- Fully scanned documents
- Large graphical elements
- Embedded image-based tables

### Vision Strategy

- Full-page conversion for chart-heavy pages
- Gemini 2.5 Flash Vision for OCR and structured extraction
- Per-image extraction when appropriate
- Duplicate page hash prevention
- API call cap to control quota usage
- Structured normalization of extracted text
- Markdown-style reconstruction for tables

### Enables Accurate Extraction From

- Research paper figures
- Financial charts
- Image-based tables
- Scanned reports
- Graphical statistical data

> **Note:** Vision is used strictly for ingestion and extraction, not for main RAG reasoning.

---

## Hybrid Structured + LLM Reasoning

### CSV Deterministic Engine

For structured CSV queries:

- Detects numeric intent (max, min, avg, sum, count)
- Dynamically identifies numeric columns
- Uses Pandas for deterministic computation
- Bypasses LLM for numeric calculation
- Uses LLM only for explanation

### Structured PDF Tables

- Preserves row integrity
- Maintains contextual entity labels
- Prevents cross-row contamination
- Maintains numeric alignment
- Supports accurate numeric comparisons

### Benefits

- Deterministic numeric outputs
- Reduced hallucinations
- Precision in structured queries
- Clean reasoning-mode separation

---

## Format-Aware Adaptive Chunking

The ingestion pipeline dynamically selects chunking strategies.

### PDF Balanced Strategy

- Larger context windows
- Reduced fragmentation
- Paragraph grouping
- Table rows preserved as semantic units
- Metadata embedded inside structured blocks
- Reduced vector noise

### Chart-Heavy Strategy

- Entire page processed via Vision layer
- Prevents fragmented image chunking
- Preserves visual context

### CSV Strategy

- Stored directly in SQLite
- No embeddings required for deterministic numeric queries
- Vector store used only when semantic retrieval is required

### Reduces

- Embedding overhead
- Memory consumption
- Context leakage
- Retrieval ambiguity

---

## Retrieval & Ranking Architecture

The system uses:

- SentenceTransformers (`bge-small-en-v1.5`)
- Normalized embeddings
- Persistent ChromaDB vector store

### Hybrid Re-Ranking Signals

- Semantic similarity
- Keyword overlap
- Exact phrase boost
- Numeric alignment boost
- Structured row density boost
- Table integrity scoring
- Vision-content priority boost

### LLM Layer

**Primary Model:** `llama-3.3-70b-versatile`  
**Fallback Model:** `llama-3.1-8b-instant`  
Both served via **Groq**.

### LLM Behavior

- Strict context-bound prompting
- Deterministic temperature (0.1)
- No document-specific hardcoding
- No entity rule injection

### Result

- High grounding accuracy
- Stable structured retrieval
- Reliable numeric responses
- Reduced hallucination risk

---

## Automation & Persistence Layer

The system includes automated synchronization and backup mechanisms.

### APScheduler Jobs

- Daily Google Drive ingestion sync
- Scheduled vector backup
- Scheduled metadata backup

### Persistence Strategy

- SQLite → Pickle serialization → Google Drive
- ChromaDB → tar.gz compression → Google Drive
- Controlled rehydration on restart

### Benefits

- Crash recovery safety
- State durability
- Low-cost persistence
- Cloud-ready architecture
- Production-aligned reliability

---

## High-Level Architecture

```
Input Sources (Google Drive / Azure / Local)
          │
   Controlled Ingestion
          │
   Format-Aware Extraction
          │
 Gemini Vision Layer (OCR + Tables)
          │
 Adaptive Chunking
          │
 bge-small Embeddings
          │
 ChromaDB (Vector Store)
          │
 SQLite (Structured + Metadata)
          │
 Hybrid Retrieval + Structural Re-Ranking
          │
 Deterministic Engine (Pandas for CSV)
          │
 Groq Llama 3.3 (Primary)
          │
 Groq Llama 3.1 (Fallback)
          │
 Streamlit Interface
```

---

## Technical Stack

| Component | Technology |
|-----------|------------|
| Language | Python |
| PDF Extraction | pdfplumber |
| Vision/OCR | Gemini 2.5 Flash (Vision) |
| DOCX Parsing | python-docx |
| Structured Data | Pandas |
| Embeddings | sentence-transformers (`bge-small-en-v1.5`) |
| Vector Store | ChromaDB |
| Metadata Store | SQLite |
| LLM Backend | Groq |
| Primary Model | `llama-3.3-70b-versatile` |
| Fallback Model | `llama-3.1-8b-instant` |
| Scheduler | APScheduler |
| Persistence | Google Drive Backups |
| Frontend | Streamlit |

---

## Running the System

### 1️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

### 2️⃣ Set Environment Variables

Create a `.env` file:

```
GROQ_API_KEY=your_key_here
GEMINI_API_KEY=your_key_here
POPPLER_PATH=optional_windows_path_if_needed
```

### 3️⃣ Ingest Documents

```bash
python -m src.ingestion.main
```

### 4️⃣ Launch UI

```bash
streamlit run scripts/app.py
```

Open in browser:

```
http://localhost:8501
```

---

## Repository Status

###  Stable

- Multi-format ingestion
- Gemini-based Vision OCR
- Structured PDF table preservation
- Deterministic CSV computation
- Hybrid semantic + lexical retrieval
- Structural re-ranking boosts
- Strict document-grounded generation
- Persistent vector storage
- APScheduler background jobs
- Google Drive auto-sync
- Automated vector + metadata backup

---

## System Characteristics

- No document-specific hardcoding
- Fully data-driven ranking
- Deterministic numeric reasoning
- Vision-aware but quota-controlled
- Production-extensible architecture
- Backup-safe and crash-resilient

---

## Next Phase

- FastAPI backend migration
- Docker containerization
- Cloud deployment
- Observability and monitoring
- Structured logging cleanup
