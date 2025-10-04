# [WAVE2-B] Weaviate Embeddings - Vector Search Implementation

**Labels:** `weaviate`, `p1-high`, `wave2-poc`, `ready-for-dev`

## Objective
Implement Weaviate vector database with manual embeddings for document chunks and search capabilities.

## Background
Need to store and search document embeddings for semantic search functionality. Using manual vectors to avoid model dependencies in the PoC.

## Tasks

### 1. Weaviate Schema Setup
- [ ] Create `DocChunk` class in Weaviate with:
  - `chunkText`: text field for document content
  - `vector`: vector field for embeddings (manual)
  - `repo`: text field for repository reference
  - `file`: text field for file path
  - `chunkId`: text field for unique chunk identifier

### 2. Analyzer Service Updates
- [ ] Add `/embed` endpoint (POST) that accepts `list[str]` of text chunks
- [ ] Generate fake/dummy vectors for PoC (or use tiny local model if available)
- [ ] Write chunks to Weaviate `DocChunk` class
- [ ] Return mapping of chunk IDs to vectors

### 3. Search Endpoint Implementation
- [ ] Add `/search` endpoint (GET) with query parameter `q`
- [ ] Implement cosine similarity search with `top-k=3`
- [ ] Return matching chunks ranked by similarity score

### 4. Integration Points
- [ ] Connect embeddings to existing analyzer workflow
- [ ] Ensure proper error handling for Weaviate operations
- [ ] Add health checks for Weaviate connectivity

## API Specifications

### POST /embed
**Request:**
```json
{
  "chunks": [
    "def process_data():\n    return result",
    "SELECT * FROM users WHERE active = true"
  ],
  "repo": "myorg/myrepo",
  "file": "/path/to/file.py"
}
```

**Response:**
```json
{
  "embeddings": [
    {
      "chunkId": "chunk_001",
      "vector": [0.1, 0.2, 0.3, ...]
    }
  ]
}
```

### GET /search?q=python function
**Response:**
```json
{
  "results": [
    {
      "chunkText": "def process_data():\n    return result",
      "score": 0.95,
      "metadata": {
        "repo": "myorg/myrepo",
        "file": "/path/to/file.py"
      }
    }
  ]
}
```

## Acceptance Criteria

- [ ] `curl http://localhost:8013/embed` with 2 strings returns vectors
- [ ] `/search?q=function` returns those strings ranked by similarity
- [ ] Weaviate contains `DocChunk` class with proper schema
- [ ] Integration works with existing analyzer service

## Dependencies
- Weaviate running (Docker/Podman)
- Existing analyzer service
- Python Weaviate client library

## Risk Mitigation
- Keep manual vectors as planned for PoC to avoid model dependencies
- Implement proper error handling for Weaviate connection issues