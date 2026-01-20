# GenAI RAG System – Learning & Design Phase

## Overview
This repository is created as part of my internship learning phase to understand and design a **Retrieval-Augmented Generation (RAG)** based system for document querying and chatbot-style interactions.

The initial focus of this repository is on **conceptual understanding, architecture design, and documentation**, before moving towards implementation.

---

## What is Retrieval-Augmented Generation (RAG)?
Retrieval-Augmented Generation (RAG) is an approach where relevant information is first retrieved from a document source and then provided as context to a Large Language Model (LLM) to generate accurate and grounded responses.

RAG helps overcome limitations of plain LLM-based systems by reducing hallucinations and improving response relevance.

---

## Key Components of a RAG System
Based on initial study and research, a typical RAG pipeline consists of the following components:

1. **Document Ingestion**
   - Source documents are collected and prepared for processing.

2. **Chunking**
   - Large documents are split into smaller, meaningful chunks to preserve context.

3. **Embeddings**
   - Text chunks are converted into numerical vector representations that capture semantic meaning.

4. **Vector Database**
   - Stores embeddings and enables semantic similarity search.

5. **Retriever**
   - Retrieves the most relevant document chunks based on a user query.

6. **Large Language Model (LLM)**
   - Generates responses using the retrieved document context.

---

## Current Status
- Studying fundamentals of RAG and its real-world use cases.
- Reviewing technical articles and reference material.
- Organizing learnings using tools like NotebookLM.
- Understanding end-to-end RAG workflows at a high level.

---

## Next Steps
- Deep dive into individual RAG components and their roles.
- Draft a high-level architecture flow for a generic RAG system.
- Gradually evolve this repository to include design diagrams and implementation code.
