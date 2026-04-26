# User Guide

## Overview

KB AI RAG is a chat interface for querying a private knowledge base. You ask questions in natural language; the system retrieves relevant document excerpts and generates a grounded answer with source citations.

---

## Accessing the Application

Once the stack is running, open **http://localhost:3000** in your browser.

---

## Asking Questions

1. Type your question in the input box at the bottom of the screen.
2. Press **Enter** or click the send button.
3. The answer streams in as it is generated.

Each response includes:
- **Answer** — generated from the retrieved knowledge articles.
- **Citations** — source document names and the specific excerpts used.
- **Confidence badge** — an indicator of retrieval quality.

---

## Managing Sessions

- Each browser session starts a new conversation context.
- Previous conversations are listed in the **sidebar** on the left.
- Click any past session to reload it.

---

## Uploading / Adding Documents

Documents are loaded at the server level (not via the UI). Ask your administrator to place PDF or `.txt` files in the `data/knowledge/` folder and trigger a re-ingest. See the [Deployment Guide](deployment-guide.md) for details.

---

## Supported Document Types

| Format | Notes |
|---|---|
| PDF | Text-based PDFs; scanned images are not supported |
| Plain text (`.txt`) | UTF-8 encoding |

---

## Limitations

- The system only answers questions from the ingested knowledge base. It will not browse the internet or answer general knowledge questions outside your documents.
- Very long documents are chunked; the answer may not reflect every section of a document.
- Confidence scores are heuristic — verify critical answers against the cited source.
