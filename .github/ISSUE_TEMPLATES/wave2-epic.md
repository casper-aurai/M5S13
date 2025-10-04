# [WAVE2] Complete Wave 2 Implementation - Demo-Credible Pipeline

**Labels:** `wave2-poc`, `p0-critical`, `ready-for-dev`

## Objective
Transform the current Dgraph PoC into a demo-credible pipeline with complete data flow, observability, and production-ready tooling.

## Overview
This is the comprehensive Wave 2 implementation that builds upon the Dgraph foundation to create a fully functional, observable, and maintainable data pipeline.

## Epic Tasks (A-F in Priority Order)

### A. Kafka Wiring `[p0-critical]`
- [ ] Complete event flow: ingestion→miner→analyzer→writer
- [ ] Implement proper message schemas and formats
- [ ] Add Kafka producers/consumers to all services
- [ ] Expose metrics and health endpoints

### B. Weaviate Embeddings `[p1-high]`
- [ ] Create DocChunk class with manual vectors
- [ ] Add `/embed` and `/search` endpoints to analyzer
- [ ] Implement vector search functionality

### C. Reporting Service `[p1-high]`
- [ ] Generate Markdown reports with Mermaid diagrams
- [ ] Query Dgraph and upload to MinIO
- [ ] Include KPIs, visualizations, and metadata

### D. Airflow DAG E2E `[p1-high]`
- [ ] Replace stubs with real HTTP calls and Kafka polling
- [ ] Implement proper error handling and timeouts
- [ ] Parameterize repo and ensure successful runs

### E. Observability Stack `[p2-medium]`
- [ ] Prometheus metrics collection from all services
- [ ] Loki log aggregation with structured logging
- [ ] Grafana dashboard with Throughput/Latency/Errors

### F. DX & Hardening `[p2-medium]`
- [ ] `make topics` and `make demo` targets
- [ ] Pre-commit hooks (black, ruff, mypy)
- [ ] Health checks and seed scripts

## Success Criteria

- [ ] Complete pipeline processes real repository data
- [ ] All services communicate via Kafka topics
- [ ] Reports generated and stored in MinIO
- [ ] Grafana shows real-time metrics during operation
- [ ] One-command demo (`make demo`) works end-to-end
- [ ] Code quality gates in place

## Architecture
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Ingestion     │───▶│     Miner       │───▶│   Analyzer      │
│   (Kafka Pub)   │    │   (Kafka Sub/   │    │   (Kafka Sub/   │
│                 │    │    Pub)         │    │    Pub)         │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ repos.ingested  │    │  code.mined     │    │ code.analyzed   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Writer        │◀───│   Dgraph       │    │   Weaviate     │
│ (Kafka Sub/Pub) │    │   (Upserts)     │    │  (Embeddings)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  graph.apply    │    │   Reports/      │    │   Grafana/     │
│   (Metrics)     │    │   MinIO         │    │   Prometheus   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Verification Checklist

- [ ] `make up` → all services healthy
- [ ] `make topics` → Kafka topics created
- [ ] Repository trigger → data flows through all topics
- [ ] Reports generated and visible in MinIO
- [ ] Grafana dashboard shows throughput during operation
- [ ] `make demo` → complete end-to-end execution

## Getting Started

1. **Start Services**: `make up`
2. **Create Topics**: `make topics`
3. **Run Demo**: `make demo`
4. **Verify Results**:
   - Check Kafka topics for message flow
   - Verify MinIO reports
   - Monitor Grafana dashboard
   - Query Dgraph for new nodes

## Branch Strategy
- Create branch: `poc/wave2`
- Implement tasks in priority order A→F
- Regular commits with clear messages
- PR when all acceptance criteria met