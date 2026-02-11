# GenAI RAG System – Design, Implementation & Deployment Planning Phase

## Overview

This repository contains the implementation of a Retrieval-Augmented Generation (RAG) based document querying system developed during my internship.

The project has evolved from conceptual exploration to a fully working end-to-end RAG pipeline capable of ingesting structured documents from Google Drive, performing semantic retrieval, and generating grounded responses using a local LLM.

Current focus areas:

- Retrieval quality improvements
- Multi-format ingestion
- Chunking strategy optimization
- System architecture design
- Cost-effective deployment planning


---

## System Capabilities

### 1. End-to-End RAG Pipeline

- Google Drive document ingestion via Drive API
- Automated text extraction
- Format-aware chunking
- BGE-M3 embedding generation
- Persistent vector storage using ChromaDB
- Semantic retrieval with similarity scoring
- Dominant-document selection logic
- Section-aware context construction
- LLM-based grounded response generation using Ollama
- Streamlit-based chat interface
- Source attribution included in responses


### 2. Supported Input Formats

| Format       | Extraction Method              | Chunking Strategy   |
|-------------|--------------------------------|---------------------|
| Google Docs | API-based text extraction       | Paragraph-based     |
| DOCX        | python-docx extraction          | Paragraph-based     |
| PDF         | PyMuPDF extraction              | Paragraph-based     |
| CSV (Planned) | Structured parsing            | Row-based           |


### 3. Retrieval Improvements

- Migrated from token-based chunking to paragraph-based chunking for improved semantic integrity
- Upgraded embeddings to BGE-M3 for improved query-document alignment
- Implemented dominant-document selection using:
  - Semantic similarity (vector search)
  - Keyword overlap scoring (document-level filtering only)
- Added section-aware context extraction to reduce cross-section mixing
- Introduced fallback LLM model for fail-safe response generation

Results:

- Improved grounding accuracy
- Reduced hallucination risk
- Explainable retrieval through detailed logs


---

## Current Architecture (High-Level)

Google Drive  
→ Text Extraction  
→ Format-aware Chunking  
→ BGE-M3 Embeddings  
→ ChromaDB (Persistent Vector Store)  
→ Semantic Retrieval  
→ Dominant Document Filtering  
→ Section-aware Context Construction  
→ Ollama LLM (Primary + Fallback)  
→ Streamlit UI  


---

## Technical Stack

- Python
- Google Drive API
- PyMuPDF (PDF extraction)
- python-docx
- SentenceTransformers (BGE-M3)
- ChromaDB
- Ollama (Local LLM)
- Streamlit
- SQLite (Tracker DB)


---

## Current Focus

- Enhancing retrieval robustness for documents with overlapping terminology
- Improving chunking strategies based on input format
- Adding CSV ingestion with row-based chunking
- Designing system architecture diagrams
- Exploring cost-effective deployment strategies (e.g., Azure Blob Storage, containerized backend services)


---

## Next Steps

- Add CSV ingestion support with structured row-based chunking
- Implement adaptive chunking strategies depending on document type
- Refactor backend into FastAPI for scalable API-based serving
- Design and document full system architecture
- Plan cost-efficient deployment (cloud storage + scalable inference layer)


---

## Repository Status

The project is currently in an advanced Proof-of-Concept stage with a stable ingestion, retrieval, and generation pipeline.

The next phase focuses on:

- Architecture hardening
- Deployment design
- Production-readiness improvements
