# GenAI RAG System - Design, Implementation & Architecture

>
Overview:

This repository contains the implementation of a Retrieval-Augmented Generation (RAG) based document querying system developed during an advanced internship project. The system has evolved from a basic RAG prototype into a multi-format, hybrid-reasoning architecture capable of ingesting structured and unstructured documents from Google Drive, performing format-aware chunking, generating semantic embeddings, and producing grounded responses using both structured computation and LLM-based reasoning. The project is now focused on architecture refinement, structured reasoning enhancement, and deployment readiness.
---

## Table of Contents

- [Overview](#overview)
- [Core Capabilities](#core-capabilities)
- [Supported Input Formats](#supported-input-formats)
- [Hybrid Structured + LLM Reasoning](#hybrid-structured--llm-reasoning)
- [Format-Aware Adaptive Chunking](#format-aware-adaptive-chunking)
- [Retrieval Improvements](#retrieval-improvements)
- [High-Level Architecture](#high-level-architecture)
- [Technical Stack](#technical-stack)
- [Current Focus](#current-focus)
- [Next Phase](#next-phase)
- [Repository Status](#repository-status)

---

## Overview

The system evolved from a basic prototype into a multi-format, hybrid-reasoning architecture capable of:

- Ingesting structured and unstructured documents from Google Drive
- Performing format-aware adaptive chunking
- Generating high-quality semantic embeddings
- Executing deterministic structured computation for tabular data
- Producing grounded responses using LLM-based reasoning
- Maintaining storage consistency across ingestion cycles

The project is currently in the **architecture refinement and production-readiness** phase.

---

## Core Capabilities

### End-to-End RAG Pipeline

- Google Drive ingestion via Drive API
- Multi-format document extraction
- Format-aware chunking strategy selection
- BGE-M3 embedding generation
- Persistent vector storage using ChromaDB
- Semantic similarity retrieval with scoring
- Dominant-document filtering logic
- Section-aware context construction

### Hybrid Reasoning

- Structured CSV numeric reasoning
- LLM-based contextual reasoning
- Automatic fallback LLM support

### Interface & Observability

- Streamlit-based chat interface
- Source attribution in responses
- Detailed retrieval logging for explainability

---

## Supported Input Formats

| Format | Extraction Method | Chunking Strategy | Reasoning Mode |
|---|---|---|---|
| Google Docs | Drive API | Paragraph-based | LLM |
| DOCX | python-docx | Paragraph-based | LLM |
| PDF | PyMuPDF | Paragraph-based | LLM |
| CSV | Pandas parsing | Row-based structured text | Hybrid |

---

## Hybrid Structured + LLM Reasoning

The system introduces a hybrid reasoning layer for structured datasets.

### CSV Structured Reasoning

For CSV queries, the system:

1. **Detects numeric intent** — Maximum, Minimum, Average, Sum, Count
2. **Automatically identifies** the relevant numeric column
3. **Performs deterministic computation** using Pandas
4. **Applies date-aware formatting** where applicable
5. **Bypasses the LLM** for purely numeric queries
6. **Falls back to LLM** when structured reasoning is insufficient

### Benefits

| Benefit | Description |
|---|---|
| Deterministic responses | No variability in numeric outputs |
| Zero hallucinated calculations | Computation is always Pandas-driven |
| Faster response time | LLM overhead skipped for structured queries |
| Clear separation | Retrieval and computation are decoupled |

---

## Format-Aware Adaptive Chunking

The ingestion pipeline dynamically selects chunking strategies based on document type:

- **Paragraph-based chunking** — for Docs, DOCX, and PDF files
- **Row-based chunking** — for CSV files

This improves:

- Semantic integrity
- Retrieval precision
- Context grounding
- Reduced cross-document contamination

---

## Retrieval Improvements

Key retrieval enhancements include:

- Upgraded embeddings to **BGE-M3**
- Migration from token-based to **paragraph-based chunking**
- **Dominant-document selection** using:
  - Vector similarity scoring
  - Keyword overlap scoring (document-level filtering only)
- Section-aware context grouping
- Reduced cross-document mixing
- Structured reasoning bypass for CSV numeric queries
- Enhanced logging for explainable retrieval decisions

### Outcomes

- Improved grounding accuracy
- Reduced hallucination risk
- Better performance on documents with overlapping terminology
- Deterministic structured responses for CSV datasets

---

## High-Level Architecture

```
Google Drive
    |
Format-Aware Extraction
    |
Paragraph / Row-Based Chunking
    |
BGE-M3 Embeddings
    |
ChromaDB (Persistent Vector Store)
    |
Semantic Retrieval
    |
Dominant Document Filtering
    |
Section-Aware Context Construction
    |
Hybrid Reasoning Layer
    |-- Structured CSV Engine (Pandas)
    |-- LLM Reasoning (Primary + Fallback)
    |
Streamlit UI
```

---

## Technical Stack

| Component | Technology |
|---|---|
| Language | Python |
| Drive Integration | Google Drive API |
| PDF Extraction | PyMuPDF |
| DOCX Extraction | python-docx |
| Structured Data | Pandas |
| Embeddings | SentenceTransformers (BGE-M3) |
| Vector Store | ChromaDB |
| Tracker Database | SQLite |
| LLM Backend | Local or API-based |
| Frontend | Streamlit |

---

## Current Focus

- [ ] Strengthening dominant-document filtering
- [ ] Improving numeric intent detection
- [ ] Refining section-aware context construction
- [ ] Refactoring toward API-first backend (FastAPI)
- [ ] Designing scalable production architecture
- [ ] Cost-aware deployment planning

---

## Next Phase

- [ ] Backend refactor to **FastAPI**
- [ ] Modular hybrid reasoning engine
- [ ] Adaptive chunk sizing heuristics
- [ ] Retrieval and grounding evaluation metrics
- [ ] Production deployment architecture design
- [ ] Containerized inference services
- [ ] Monitoring and observability integration

---

## Repository Status

> **Advanced Proof-of-Concept** — stable for multi-format ingestion and hybrid reasoning; production hardening in progress.

**Stable:**
- Multi-format ingestion
- Robust semantic retrieval
- Hybrid structured + LLM reasoning
- Deterministic CSV computation
- Grounded response generation with source attribution

**In Progress:**
- Architecture hardening
- Scalability improvements
- Production-readiness
