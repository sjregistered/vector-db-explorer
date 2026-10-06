# Vector DB Explorer

**RTB Cycle 16 – Generative AI Advance · Milestone 5 (Vector Databases)**

A premium dark-themed dashboard for managing a **ChromaDB** vector database:
full CRUD, semantic similarity search, text-chunking previews, and embedding visualization.

## Features

| Tab | What it does |
|-----|--------------|
| **Collections** | Create / list / delete collections (cosine distance by default) |
| **Documents** | Insert, view, edit (auto re-embedding) and delete documents |
| **Search** | Top-K similarity search with similarity + distance scores and latency |
| **Chunking** | Compare sentence / character / word / paragraph chunking strategies |
| **Visualize** | 2D PCA projection of embeddings + cosine similarity heatmap |

- Embeddings: `sentence-transformers/all-MiniLM-L6-v2` (384 dims)
- Storage: `chromadb.PersistentClient` → `./chroma_explorer_db/`

## Quick Start

```bash
cd vector-db-explorer
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open **http://127.0.0.1:5001**. The embedding model (~90 MB) is downloaded on first use.

## REST API

| Method | Endpoint | Body / Params |
|--------|----------|---------------|
| GET | `/api/collections` | – |
| POST | `/api/collections` | `{ "name": "my_col" }` |
| DELETE | `/api/collections/<name>` | – |
| GET | `/api/collections/<name>/stats` | – |
| GET | `/api/documents` | `?collection=&limit=&offset=` |
| POST | `/api/documents` | `{ "collection", "documents": [..], "ids"?: [..] }` |
| PUT | `/api/documents/<id>` | `{ "collection", "document", "metadata"? }` |
| DELETE | `/api/documents/<id>` | `?collection=` |
| POST | `/api/search` | `{ "collection", "query", "top_k" }` |
| POST | `/api/chunk` | `{ "text", "method", ...size params }` |
| GET | `/api/embeddings/info` | – |
| POST | `/api/embeddings/visualize` | `{ "texts": [..] }` (2–100 items) |

## Project Structure

```
vector-db-explorer/
├── app.py               # Flask app + REST API
├── src/
│   ├── db_manager.py    # ChromaDB CRUD + search
│   ├── chunking.py      # Chunking strategies
│   └── embeddings.py    # Embeddings, similarity matrix, PCA
├── templates/index.html
└── static/{css,js}/
```
