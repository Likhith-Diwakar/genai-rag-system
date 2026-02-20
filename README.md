# GenAI RAG System — Design, Implementation & Architecture Overview

This repository contains the implementation of a Retrieval-Augmented Generation (RAG) based document querying system developed during an advanced internship project. The system has evolved from a basic RAG prototype into a modular, multi-format, hybrid-reasoning architecture capable of ingesting structured and unstructured documents from multiple sources, performing format-aware chunking, generating semantic embeddings, and producing grounded responses using both structured computation and LLM-based reasoning.

Following recent architecture review discussions, the system is now transitioning toward a production-oriented, modular, scheduled-sync pipeline with cloud backup and API-first design.

---

## Table of Contents

- [Overview](#overview)
- [Core Capabilities](#core-capabilities)
- [Supported Input Formats](#supported-input-formats)
- [Hybrid Structured + LLM Reasoning](#hybrid-structured--llm-reasoning)
- [Format-Aware Adaptive Chunking](#format-aware-adaptive-chunking)
- [Retrieval Improvements](#retrieval-improvements)
- [Scheduled Sync & Backup Architecture](#scheduled-sync--backup-architecture)
- [Modular LLM & Input Source Design](#modular-llm--input-source-design)
- [High-Level Architecture](#high-level-architecture)
- [Technical Stack](#technical-stack)
- [Current Focus](#current-focus)
- [Next Phase](#next-phase)
- [Repository Status](#repository-status)

---

## Overview

The system has evolved into a modular hybrid-reasoning architecture capable of:

- Ingesting structured and unstructured documents from Google Drive and Azure Blob
- Performing format-aware adaptive chunking
- Extracting structured tables from PDFs using `pdfplumber`
- Generating high-quality semantic embeddings using BGE-M3
- Executing deterministic structured computation for tabular data
- Producing grounded responses using configurable LLM backends
- Maintaining persistent vector and relational storage
- Performing scheduled ingestion sync and automated backup

The project is now in the **architecture hardening and modularization phase**, preparing for API-first backend transition and production deployment.

---

## Core Capabilities

### End-to-End RAG Pipeline

- Pluggable input source connectors (Drive, Blob)
- Multi-format document extraction
- Format-aware chunking strategy selection
- BGE-M3 embedding generation
- Persistent vector storage using ChromaDB
- SQLite-based ingestion tracking & metadata storage
- Semantic similarity retrieval with scoring
- Dominant-document filtering logic
- Section-aware context construction

### Hybrid Reasoning

- Structured CSV numeric reasoning (Pandas)
- LLM-based contextual reasoning
- Configurable primary + fallback LLM
- Modular LLM selection without affecting pipeline

### Interface & Observability

- Streamlit-based UI (temporary frontend)
- Source attribution in responses
- Detailed retrieval logging
- Clear separation of ingestion, embedding, retrieval, and reasoning layers

---

## Supported Input Formats

| Format      | Extraction Method             | Chunking Strategy         | Reasoning Mode |
|-------------|-------------------------------|---------------------------|----------------|
| Google Docs | Drive API                     | Paragraph-based           | LLM            |
| DOCX        | python-docx                   | Paragraph-based           | LLM            |
| PDF         | pdfplumber (Text + Tables)    | Paragraph-based           | LLM            |
| CSV         | Pandas parsing                | Row-based structured text | Hybrid         |

---

## Hybrid Structured + LLM Reasoning

The system implements a hybrid reasoning layer for structured datasets.

### CSV Structured Reasoning

For CSV queries, the system:

1. Detects numeric intent (Max, Min, Average, Sum, Count)
2. Identifies relevant numeric column automatically
3. Performs deterministic computation using Pandas
4. Bypasses LLM for purely numeric queries
5. Falls back to LLM when contextual reasoning is required

### Benefits

| Benefit                        | Description                          |
|--------------------------------|--------------------------------------|
| Deterministic responses        | No variability in numeric outputs    |
| Zero hallucinated calculations | Pandas-driven computation            |
| Faster response time           | Skips LLM when unnecessary           |
| Clean separation               | Retrieval and reasoning decoupled    |

---

## Format-Aware Adaptive Chunking

The ingestion pipeline dynamically selects chunking strategies:

- **Paragraph-based chunking** — Docs, DOCX, PDF
- **Row-based chunking** — CSV

PDF extraction now supports:

- Table extraction using `pdfplumber`
- Structured row formatting
- Image detection (future OCR extension)

This improves semantic integrity, retrieval grounding, cross-document contamination reduction, and handling of financial and structured tables.

---

## Retrieval Improvements

Key retrieval enhancements include:

- BGE-M3 embeddings
- Paragraph-level semantic chunking
- Dominant-document selection using vector similarity and keyword overlap scoring
- Section-aware context construction
- Reduced cross-document mixing
- Structured reasoning bypass for CSV numeric queries

**Outcomes:** improved grounding accuracy, reduced hallucination risk, better performance on overlapping terminology, and deterministic CSV reasoning.

---

## Scheduled Sync & Backup Architecture

Following architecture discussions, ingestion now moves toward a scheduled synchronization model.

### Scheduled Ingestion

- Ingestion runs once daily (e.g., 3 AM)
- Automatic Drive/Blob sync
- No continuous polling
- Designed for event-based evolution

### Vector Store Backup

At scheduled sync time:

1. ChromaDB vector data is serialized (pickle)
2. Pickled vector snapshot uploaded to Google Drive
3. During next sync: snapshot restored and rehydrated into ChromaDB

### SQLite Backup

1. SQLite tracker DB is backed up daily
2. Snapshot stored to Drive
3. Restored during sync — ensures ingestion log continuity

### Benefits

- Disaster recovery capability
- Cloud-based backup
- Consistent daily state snapshot
- Production-safe storage design

---

## Modular LLM & Input Source Design

### Multi-LLM Support

The system is evolving into a modular LLM abstraction layer where:

- Users can select any LLM backend
- Primary and fallback LLMs are configurable
- Pipeline logic remains unaffected
- Embedding, retrieval, and reasoning remain decoupled

Planned abstraction:

```
LLM Interface
    |
Provider Adapter (Groq / OpenAI / Local / etc.)
```

### Pluggable Input Sources

Currently supported: Google Drive, Azure Blob Storage. Designed to support future connectors without pipeline modification.

---

## High-Level Architecture

```
Input Sources (Drive / Blob)
        |
Scheduled Sync (3 AM Daily)
        |
Format-Aware Extraction
        |
Paragraph / Row-Based Chunking
        |
BGE-M3 Embeddings
        |
ChromaDB (Vector Store) ── SQLite (Metadata + Tracker)
        |
Daily Backup (Pickle → Drive)
        |
Semantic Retrieval
        |
Dominant Document Filtering
        |
Section-Aware Context Construction
        |
Hybrid Reasoning Layer
    |-- Structured CSV Engine (Pandas)
    |-- Modular LLM Engine (Primary + Fallback)
        |
FastAPI Backend (Planned)
        |
Frontend (Temporary: Streamlit)
```

---

## Technical Stack

| Component            | Technology                    |
|----------------------|-------------------------------|
| Language             | Python                        |
| Drive Integration    | Google Drive API              |
| Blob Storage         | Azure SDK                     |
| PDF Extraction       | pdfplumber                    |
| DOCX Extraction      | python-docx                   |
| Structured Data      | Pandas                        |
| Embeddings           | SentenceTransformers (BGE-M3) |
| Vector Store         | ChromaDB                      |
| Tracker Database     | SQLite                        |
| Serialization        | Pickle                        |
| Backend (Planned)    | FastAPI                       |
| Frontend (Temporary) | Streamlit                     |

---

## Current Focus

- [ ] Implement scheduled 3 AM sync
- [ ] Vector DB snapshot + Drive backup
- [ ] SQLite snapshot + Drive backup
- [ ] Modular LLM abstraction layer
- [ ] Pluggable input connector interface
- [ ] FastAPI backend migration
- [ ] Remove Streamlit-dependent ingestion logic
- [ ] Architecture cleanup and refactoring

---

## Next Phase

- FastAPI backend refactor
- Background scheduler integration
- Multi-LLM dynamic selection
- Production-ready storage recovery logic
- API-first architecture
- Containerization
- Monitoring & observability
- Event/webhook-based ingestion

---

## Repository Status

**Advanced Modular RAG System** — transitioning from prototype to production-oriented pipeline.

**Stable:**
- Multi-format ingestion
- Structured + LLM hybrid reasoning
- Persistent vector storage
- PDF structured extraction
- Deterministic CSV computation
- Grounded answer generation

**In Progress:**
- Scheduled sync architecture
- Daily backup & restore mechanism
- Modular LLM abstraction
- Input source decoupling
- FastAPI migration
- Production hardening
