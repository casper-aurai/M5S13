# [WAVE2-A] Kafka Wiring - Complete Event Flow Pipeline

**Labels:** `kafka`, `p0-critical`, `wave2-poc`, `ready-for-dev`

## Objective
Implement complete Kafka event flow from ingestion→miner→analyzer→writer with proper message schemas and metrics.

## Background
Currently the pipeline has stubs. This task implements the actual data flow through Kafka topics with proper message formats and consumer/producer implementations.

## Tasks

### 1. Create Kafka Topics
- [ ] Create topic: `repos.ingested`
- [ ] Create topic: `code.mined`
- [ ] Create topic: `code.analyzed`
- [ ] Create topic: `graph.apply`
- [ ] Add `make topics` target to create topics idempotently

### 2. Ingestion Service Updates
- [ ] Modify `/trigger?repo=...` to publish to `repos.ingested` topic
- [ ] Include `repo/name/ref/paths` in message payload
- [ ] Add timestamp field `ts` in ISO format

### 3. Miner Service Updates
- [ ] Add Kafka consumer for `repos.ingested` topic
- [ ] Implement file scanning for `.py`, `.sql` files
- [ ] Publish file summaries to `code.mined` topic
- [ ] Include `repo`, `file`, `lang`, `size`, `hash`, `ts` fields

### 4. Analyzer Service Updates
- [ ] Add Kafka consumer for `code.mined` topic
- [ ] Implement lightweight analysis (function counts, table refs)
- [ ] Publish findings to `code.analyzed` topic
- [ ] Include `repo`, `file`, `lang`, `findings`, `ts` fields

### 5. Writer Service Updates
- [ ] Add Kafka consumer for `code.analyzed` topic
- [ ] Implement Dgraph upserts for nodes/edges
- [ ] Publish acknowledgment to `graph.apply` topic
- [ ] Expose `/writer/health` with incremented counters

## Message Schemas

### repos.ingested
```json
{
  "repo": "dbt-labs/jaffle-shop-classic",
  "ref": "main",
  "path": "/data/jaffle",
  "ts": "2024-01-01T12:00:00Z"
}
```

### code.mined
```json
{
  "repo": "dbt-labs/jaffle-shop-classic",
  "file": "/data/jaffle/models/orders.sql",
  "lang": "sql",
  "size": 1234,
  "hash": "sha256-hash",
  "ts": "2024-01-01T12:00:00Z"
}
```

### code.analyzed
```json
{
  "repo": "dbt-labs/jaffle-shop-classic",
  "file": "/data/jaffle/models/orders.sql",
  "lang": "sql",
  "findings": {
    "tables": ["orders", "customers"]
  },
  "ts": "2024-01-01T12:00:00Z"
}
```

## Acceptance Criteria

- [ ] `kafkacat -b localhost:9092 -C -t code.analyzed -o -5 -e` shows messages after `/trigger`
- [ ] `/writer/health` shows incremented counters
- [ ] All services properly consume and produce messages in correct format
- [ ] Error handling for malformed messages

## Dependencies
- Kafka running on Podman
- Existing ingestion/miner/analyzer/writer services

## Risk Mitigation
- If Kafka on Podman causes issues, be prepared to switch to Redpanda
- Implement proper error handling and dead letter queues