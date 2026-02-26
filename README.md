# GenAI RAG System  
## Design, Implementation & Architecture Overview

A modular, multi-format, hybrid-reasoning **Retrieval-Augmented Generation (RAG)** system capable of:

- Ingesting structured and unstructured documents  
- Performing format-aware chunking  
- Generating semantic embeddings  
- Producing grounded responses using both deterministic computation and LLM-based reasoning  

---

## Table of Contents

- [Overview](#overview)
- [Core Capabilities](#core-capabilities)
- [Supported Input Formats](#supported-input-formats)
- [Vision + OCR Pipeline](#vision--ocr-pipeline)
- [Hybrid Structured + LLM Reasoning](#hybrid-structured--llm-reasoning)
- [Format-Aware Adaptive Chunking](#format-aware-adaptive-chunking)
- [Retrieval & Ranking Architecture](#retrieval--ranking-architecture)
- [High-Level Architecture](#high-level-architecture)
- [Technical Stack](#technical-stack)
- [Running the System](#running-the-system)
- [Repository Status](#repository-status)
- [System Characteristics](#system-characteristics)
- [Next Phase](#next-phase)

---

## Overview

This repository contains an advanced Retrieval-Augmented Generation (RAG) system designed to handle:

- Structured documents (CSV)
- Unstructured documents (PDF, DOCX)
- PDFs containing scanned pages
- Embedded tables inside PDFs
- Chart-heavy research papers
- Hybrid semantic + lexical retrieval
- Deterministic structured computation
- Strict context-grounded generation

The system is modular, extensible, ingestion-safe, and optimized for structured precision while maintaining strong semantic reasoning for unstructured content.

The current implementation is **stable and demo-ready via Streamlit**.

---

## Core Capabilities

### End-to-End RAG Pipeline

- Multi-format document ingestion
- Format-aware extraction logic
- Vision-based OCR for scanned and image-heavy PDFs
- Structured table-aware chunking
- Adaptive chunk sizing
- Lightweight semantic embeddings
- Persistent vector storage (ChromaDB)
- SQLite metadata + CSV structured storage
- Hybrid semantic + lexical retrieval
- Re-ranking with structural boosts
- Strict document-grounded LLM prompting
- Source attribution in UI

---

## Supported Input Formats

| Format | Extraction Method | Chunking Strategy | Reasoning Mode |
|--------|------------------|------------------|----------------|
| PDF (Text-based) | pdfplumber | Balanced structural chunking | LLM |
| PDF (Chart-heavy) | Full-page Vision extraction | Context-preserving chunking | LLM |
| PDF (Scanned) | Vision API (OCR fallback) | Balanced paragraph chunking | LLM |
| PDF Tables | pdfplumber table extraction | Row-aware contextual chunking | LLM |
| DOCX | python-docx | Paragraph-based | LLM |
| CSV | Pandas | SQLite structured storage | Deterministic + LLM |

---

## Vision + OCR Pipeline

The system intelligently detects when vision extraction is required.

### Trigger Conditions

- Chart-heavy pages (multiple embedded raster images)
- Sparse digital text
- Fully scanned documents
- Large embedded graphical elements

### Vision Strategy

- Full-page conversion for chart-heavy pages
- Per-image extraction when appropriate
- Duplicate hash prevention
- API call cap to avoid quota explosion
- Structured text normalization
- Markdown-style formatting for scanned tables

### Enables Question Answering From

- Research paper figures
- Embedded statistical charts
- Scanned certificates
- Image-based tabular data
- Visual placement diagrams

---

## Hybrid Structured + LLM Reasoning

### CSV Deterministic Engine

For structured CSV queries:

- Detects numeric intent (max, min, avg, sum, count)
- Dynamically identifies numeric columns
- Uses Pandas for deterministic computation
- Avoids hallucinated calculations
- Falls back to LLM only for explanation

### Structured PDF Tables

- Preserves row integrity
- Maintains contextual labels
- Retains numeric and percentage alignment
- Prevents cross-row contamination
- Enables accurate numeric comparison queries

### Benefits

- Deterministic numeric outputs
- Reduced hallucinations
- Improved precision in structured queries
- Clear reasoning-mode separation

---

## Format-Aware Adaptive Chunking

The ingestion pipeline dynamically selects chunking strategies.

### PDF Balanced Strategy

- Larger context windows
- Reduced fragmentation
- Paragraph grouping
- Table rows preserved as semantic units
- Contextual metadata embedded inside structured blocks
- Reduced vector noise

### Chart-Heavy Strategy

- Entire page processed via Vision
- Avoids fragmented image chunking
- Preserves chart context

### CSV Strategy

- Stored in SQLite
- No embedding required for deterministic queries
- Vector store used only when necessary

### Reduces

- Embedding overhead
- Memory consumption
- Context leakage
- Retrieval ambiguity

---

## Retrieval & Ranking Architecture

The system uses:

- SentenceTransformers embedding model (`bge-small-en-v1.5`)
- Normalized embeddings
- Persistent ChromaDB vector store

### Hybrid Re-Ranking Signals

- Semantic similarity
- Keyword overlap
- Exact phrase boost
- Numeric alignment boost
- Structured row density boost
- Vision-content boost

### LLM Layer

- Top-k candidate expansion
- Context-bound prompting
- Deterministic temperature (0.1)

### Design Principles

- No hardcoded entity rules
- No document-specific tuning
- Purely structural + semantic ranking signals
- Stable multi-format behavior

### Result

- High grounding accuracy
- Stable table retrieval
- Reliable numeric responses
- Reduced visual/text mixing errors

---

## High-Level Architecture

```
Input Sources (Drive / Local Files)
          │
   Controlled Ingestion
          │
   Format-Aware Extraction
          │
 Vision Detection Layer
          │
 Table-Aware Structuring
          │
 Adaptive Chunking
          │
 SentenceTransformer Embeddings
          │
 ChromaDB (Persistent Vector Store)
          │
 SQLite (Structured Data Engine)
          │
 Hybrid Retrieval + Re-ranking
          │
 Context Construction
          │
 Groq LLM (Primary + Fallback)
          │
 Streamlit Interface
```

---

## Technical Stack

| Component | Technology |
|-----------|------------|
| Language | Python |
| PDF Extraction | pdfplumber |
| Vision/OCR | Vision API |
| DOCX Parsing | python-docx |
| Structured Data | Pandas |
| Embeddings | sentence-transformers (bge-small-en-v1.5) |
| Vector Store | ChromaDB |
| Metadata Store | SQLite |
| LLM Backend | Groq (LLaMA 3.x variants) |
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

### Stable

- Multi-format ingestion
- Vision-based OCR
- Chart-heavy page detection
- Structured PDF table preservation
- Deterministic CSV computation
- Hybrid semantic + lexical retrieval
- Strict document-grounded generation
- Persistent vector storage
- Streamlit demo operational

### Optimized

- Reduced embedding explosion
- Controlled re-ranking candidate pool
- Context-length balancing
- Duplicate vision detection
- Memory-stable ingestion
- Improved structured row disambiguation

---

## System Characteristics

- No document-specific hardcoding
- No entity-level rule injection
- Fully data-driven ranking
- Deterministic numeric reasoning
- Vision-aware but quota-controlled
- Production-extensible architecture

---

## Next Phase

- FastAPI backend migration
- API-first microservice architecture
- Scheduled background ingestion
- Docker containerization
- Cloud deployment (Render / Railway / etc.)
- Background ingestion workers
- LLM abstraction layer
- Observability & monitoring
- Production logging cleanup
