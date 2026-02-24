GenAI RAG System — Design, Implementation & Architecture Overview

A modular, multi-format, hybrid-reasoning Retrieval-Augmented Generation (RAG) system capable of ingesting structured and unstructured documents, performing format-aware chunking, generating semantic embeddings, and producing grounded responses using both structured computation and LLM-based reasoning.

Table of Contents

Overview

Core Capabilities

Supported Input Formats

Vision + OCR Pipeline

Hybrid Structured + LLM Reasoning

Format-Aware Adaptive Chunking

Retrieval & Ranking Architecture

High-Level Architecture

Technical Stack

Running the System

Repository Status

Next Phase

Overview

This repository contains an advanced Retrieval-Augmented Generation (RAG) system designed to handle:

Structured documents (CSV)

Unstructured documents (PDF, DOCX)

PDFs containing scanned images

Tables embedded inside PDFs

Hybrid semantic + keyword retrieval

Deterministic structured computation

The system has evolved into a modular architecture with persistent storage, hybrid reasoning, and strict document-grounded answer generation.

The current implementation is stable and demo-ready via Streamlit.

Core Capabilities
End-to-End RAG Pipeline

Multi-format document ingestion

Format-aware extraction

Vision-based OCR for scanned PDFs

Adaptive chunking strategies

Semantic embeddings (lightweight optimized model)

Persistent vector storage (ChromaDB)

SQLite metadata + CSV structured storage

Hybrid semantic + keyword retrieval

Strict document-grounded generation

Source attribution in UI

Supported Input Formats
Format	Extraction Method	Chunking Strategy	Reasoning Mode
PDF (Text)	pdfplumber	Balanced paragraph chunking	LLM
PDF (Scanned)	Vision API + OCR	Balanced paragraph chunking	LLM
PDF Tables	pdfplumber table extraction	Structured row-aware chunking	LLM
DOCX	python-docx	Paragraph-based	LLM
CSV	Pandas	Stored in SQLite	Deterministic + LLM
Vision + OCR Pipeline

The system supports scanned PDFs via:

Raster image detection per page

Vision model extraction

Structured table interpretation from images

OCR text normalization

Clean insertion into chunking pipeline

This enables answering questions from:

Scanned research papers

Image-based tables

Graph screenshots

Embedded financial statements

Hybrid Structured + LLM Reasoning
CSV Deterministic Engine

For structured CSV queries:

Detects numeric intent (max, min, avg, sum, count)

Identifies numeric columns automatically

Uses Pandas for deterministic computation

Bypasses LLM when possible

Falls back to LLM when explanation is needed

Benefits

Zero hallucinated calculations

Deterministic numeric outputs

Faster response time

Clean reasoning separation

Format-Aware Adaptive Chunking

The ingestion pipeline dynamically selects chunking strategies:

PDF (Balanced Strategy)

Larger chunk size

Reduced fragmentation

Paragraph grouping

Table rows preserved as structured units

Reduced memory overhead

CSV

Stored directly in SQLite

No vector embedding needed for deterministic queries

This significantly reduced:

Memory usage

Embedding time

Vector explosion

Cross-chunk contamination

Retrieval & Ranking Architecture

The system uses:

SentenceTransformers embedding model (bge-small-en-v1.5)

Normalized embeddings

ChromaDB persistent vector store

Hybrid scoring:

Semantic similarity

Keyword overlap

Re-ranking

Top-k context construction

Strict context-bounded LLM prompting

Deterministic temperature (0.1)

This results in:

High grounding accuracy

Reduced hallucinations

Stable table retrieval

Clean multi-format performance

High-Level Architecture
Input Sources (Drive / Local Files)
          │
   Controlled Ingestion
          │
   Format-Aware Extraction
          │
 Vision + OCR (if needed)
          │
 Balanced Chunking Strategy
          │
 SentenceTransformer Embeddings
          │
 ChromaDB (Persistent Vector Store)
          │
 SQLite (CSV Structured Storage)
          │
 Hybrid Retrieval Layer
          │
 Context Construction
          │
 Groq LLM (Primary + Fallback)
          │
 Streamlit Interface
Technical Stack
Component	Technology
Language	Python
PDF Extraction	pdfplumber
OCR	Vision API
DOCX Parsing	python-docx
Structured Data	Pandas
Embeddings	sentence-transformers (bge-small-en-v1.5)
Vector Store	ChromaDB
Metadata Store	SQLite
LLM Backend	Groq (LLaMA 3.x variants)
Frontend	Streamlit
Running the System
1. Install Dependencies
pip install -r requirements.txt
2. Set Environment Variables

Create a .env file:

GROQ_API_KEY=your_key_here
3. Ingest Documents
python -m src.ingestion.main
4. Launch UI
streamlit run scripts/app.py

Open:

http://localhost:8501
Repository Status
Stable

Multi-format ingestion

Vision-based OCR for scanned PDFs

Balanced PDF chunking

Deterministic CSV computation

Hybrid retrieval

Strict document-grounded generation

Persistent vector storage

Streamlit demo working

Optimized

Reduced embedding overhead

Lightweight embedding model

Memory-stable ingestion

Faster embedding cycle

Clean retrieval scoring

Next Phase

FastAPI backend migration

API-first architecture

Scheduled ingestion

Cloud deployment (Render / Railway / etc.)

Docker containerization

LLM abstraction layer

Background ingestion workers

Production logging cleanup

Observability & monitoring
