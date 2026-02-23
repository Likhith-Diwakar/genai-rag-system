#  GenAI RAG System — Design, Implementation & Architecture Overview

> A modular, multi-format, hybrid-reasoning Retrieval-Augmented Generation (RAG) system capable of ingesting structured and unstructured documents, performing format-aware chunking, generating semantic embeddings, and producing grounded responses using both structured computation and LLM-based reasoning.

---

## 📋 Table of Contents

- [Overview](#overview)
- [Core Capabilities](#core-capabilities)
- [Supported Input Formats](#supported-input-formats)
- [Hybrid Structured + LLM Reasoning](#hybrid-structured--llm-reasoning)
- [Format-Aware Adaptive Chunking](#format-aware-adaptive-chunking)
- [Retrieval Improvements](#retrieval-improvements)
- [Dominant Document Filtering Logic](#dominant-document-filtering-logic)
- [Scheduled Sync & Backup Architecture](#scheduled-sync--backup-architecture)
- [Modular LLM & Input Source Design](#modular-llm--input-source-design)
- [High-Level Architecture](#high-level-architecture)
- [Technical Stack](#technical-stack)
- [Current Focus](#current-focus)
- [Next Phase](#next-phase)
- [Repository Status](#repository-status)

---

## Overview

This repository contains the implementation of a **Retrieval-Augmented Generation (RAG) based document querying system** developed during an advanced internship project. The system has evolved from a basic RAG prototype into a modular, production-oriented architecture.

The system is capable of:

- Ingesting **structured and unstructured documents** from Google Drive and Azure Blob
- Performing **format-aware adaptive chunking**
- Extracting **structured tables** from PDFs using `pdfplumber`
- Generating high-quality **semantic embeddings** using BGE-M3
- Executing **deterministic structured computation** for tabular data
- Producing **grounded responses** using configurable LLM backends
- Maintaining **persistent vector and relational storage**
- Enforcing **strict document-grounded answer generation**

> The project is currently in the **architecture hardening and production-alignment phase**, preparing for API-first backend migration and scheduled ingestion design.

---

## Core Capabilities

### End-to-End RAG Pipeline

- Pluggable input source connectors (Drive, Blob)
- Multi-format document extraction
- Format-aware chunking strategy selection
- BGE-M3 embedding generation
- Persistent vector storage using ChromaDB
- SQLite-based ingestion tracking & metadata storage
- Hybrid semantic + keyword retrieval scoring
- Dominant-document filtering to reduce cross-document contamination
- Strict context-bounded answer generation

### Interface & Observability

- Streamlit-based UI *(temporary frontend)*
- Source attribution in responses
- Detailed hybrid retrieval logging
- Aggregated dominance scoring logs
- Strict unknown response enforcement
- Clear separation of ingestion, embedding, retrieval, and reasoning layers

---

## Supported Input Formats

| Format | Extraction Method | Chunking Strategy | Reasoning Mode |
|--------|------------------|-------------------|----------------|
| Google Docs | Drive API | Paragraph-based | LLM |
| DOCX | `python-docx` | Paragraph-based | LLM |
| PDF | `pdfplumber` (Text + Tables) | Paragraph-based | LLM |
| CSV | Pandas parsing | Row-based structured text | Hybrid |

---

## Hybrid Structured + LLM Reasoning

The system implements a **hybrid reasoning layer** for structured datasets.

### CSV Structured Reasoning

For CSV queries, the system:

1. Detects **numeric intent** (Max, Min, Average, Sum, Count)
2. Identifies relevant numeric columns automatically
3. Performs **deterministic computation** using Pandas
4. Bypasses LLM for purely numeric queries
5. Falls back to LLM when contextual explanation is required

### Benefits

| Benefit | Description |
|---------|-------------|
| **Deterministic responses** | No variability in numeric outputs |
| **Zero hallucinated calculations** | Pandas-driven computation |
| **Faster response time** | Skips LLM when unnecessary |
| **Clean separation** | Retrieval and reasoning decoupled |

---

## Format-Aware Adaptive Chunking

The ingestion pipeline dynamically selects chunking strategies:

- **Paragraph-based chunking** — Docs, DOCX, PDF
- **Row-based chunking** — CSV

PDF extraction supports:
- Table extraction using `pdfplumber`
- Structured row formatting
- Clean paragraph segmentation
- Future OCR-ready architecture extension

This improves semantic integrity, retrieval grounding, cross-document contamination reduction, and handling of financial and structured tables.

---

## Retrieval Improvements

Key retrieval enhancements include:

- **BGE-M3 embeddings** for high-quality semantic encoding
- **Hybrid scoring** (semantic similarity + keyword overlap + phrase boost)
- Retrieval over expanded **top-k candidate pool**
- Post-retrieval **re-ranking**
- Strict context construction from selected document only
- LLM temperature set to `0` for deterministic generation

**Outcomes:** Improved grounding accuracy, reduced hallucination risk, improved performance on overlapping terminology, and more stable multi-document retrieval behavior.

---

## Dominant Document Filtering Logic

To prevent cross-document mixing, the system implements a **dominance selection mechanism**:

1. Retrieve top-k chunks using hybrid scoring
2. Aggregate scores per document
3. Select a **single dominant document**
4. Construct context **only from that document**
5. Disallow cross-document synthesis

Dominance scoring incorporates:
- Hybrid chunk score aggregation
- Weighted emphasis on highest-confidence chunks
- Safeguards against long-document bias

This ensures clean single-document reasoning, reduced contamination across documents, and improved precision for scoped queries.

---

## Scheduled Sync & Backup Architecture

The ingestion layer is evolving toward scheduled synchronization.

### Scheduled Ingestion *(Planned Stabilization)*

- Once-daily ingestion (target: **3 AM**)
- Controlled Drive/Blob sync
- No continuous polling
- Foundation for event-based extension

### Vector Store Snapshot

- ChromaDB persistent storage
- Snapshot serialization (pickle-based)
- Drive-based backup storage *(in progress)*
- Recovery-ready vector rehydration logic

### SQLite Backup

- SQLite tracker DB snapshot
- Drive backup support *(in progress)*
- Ingestion continuity preservation

**Benefits:** Disaster recovery capability, cloud-based backup, controlled state snapshotting, and production-safe architecture evolution.

---

## Modular LLM & Input Source Design

### Multi-LLM Support

The system supports:

- Primary + fallback LLM configuration
- Groq-based LLM integration
- Temperature-controlled deterministic generation
- LLM abstraction layer *(in progress)*

Planned abstraction:
```
LLM Interface → Provider Adapter (Groq / OpenAI / Local / etc.)
```

### Pluggable Input Sources

Currently supported:
- Google Drive
- Azure Blob Storage

Architecture designed for connector-based expansion with zero pipeline modification for new sources.

---

## High-Level Architecture

```
Input Sources (Drive / Blob)
          │
   Controlled Ingestion Sync
          │
   Format-Aware Extraction
          │
 Paragraph / Row-Based Chunking
          │
     BGE-M3 Embeddings
          │
   ChromaDB (Vector Store) ── SQLite (Metadata + Tracker)
          │
  Hybrid Semantic Retrieval
          │
  Dominant Document Selection
          │
  Strict Context Construction
          │
   Hybrid Reasoning Layer
    ├── Structured CSV Engine (Pandas)
    └── Modular LLM Engine (Primary + Fallback)
          │
   FastAPI Backend (Planned)
          │
  Frontend (Temporary: Streamlit)
```

---

## Technical Stack

| Component | Technology |
|-----------|------------|
| Language | Python |
| Drive Integration | Google Drive API |
| Blob Storage | Azure SDK |
| PDF Extraction | `pdfplumber` |
| DOCX Extraction | `python-docx` |
| Structured Data | Pandas |
| Embeddings | SentenceTransformers (BGE-M3) |
| Vector Store | ChromaDB (PersistentClient) |
| Tracker Database | SQLite |
| Serialization | Pickle |
| LLM Backend | Groq (LLaMA 3.x variants) |
| Backend *(Planned)* | FastAPI |
| Frontend *(Temporary)* | Streamlit |

---

## Current Focus

- [ ] Stabilize dominance weighting logic
- [ ] Refine retrieval score aggregation
- [ ] Implement scheduled daily sync
- [ ] Vector DB snapshot + Drive backup
- [ ] SQLite snapshot + Drive backup
- [ ] Modular LLM abstraction layer
- [ ] Pluggable input connector interface
- [ ] FastAPI backend migration
- [ ] Remove Streamlit-dependent ingestion logic
- [ ] Production-grade logging cleanup

---

## Next Phase

- FastAPI backend refactor
- Background scheduler integration
- Multi-LLM dynamic provider switching
- Production-ready storage recovery logic
- API-first architecture
- Containerization (Docker)
- Monitoring & observability
- Event/webhook-based ingestion
- Horizontal scalability planning

---

## Repository Status

**Advanced Modular RAG System — Production Transition Phase**

###  Stable

- Multi-format ingestion
- Structured + LLM hybrid reasoning
- Persistent vector storage
- PDF structured extraction
- Deterministic CSV computation
- Hybrid semantic retrieval
- Strict document-grounded generation
- Dominant document filtering logic

###  In Progress

- Scheduled sync architecture
- Vector & SQLite cloud backup
- Weighted dominance refinement
- Modular LLM abstraction
- Input source decoupling
- FastAPI migration
- Production hardening & scalability preparation

---

*Built as part of an advanced internship project. Contributions, feedback, and architecture discussions welcome.*
