# [WAVE2-E] Observability Baseline - Prometheus, Loki, Grafana

**Labels:** `observability`, `p2-medium`, `wave2-poc`, `ready-for-dev`

## Objective
Implement comprehensive observability stack with metrics collection, log aggregation, and visualization dashboard.

## Background
Need visibility into pipeline performance, throughput, and errors to ensure reliable operation and debugging capabilities.

## Tasks

### 1. Prometheus Metrics Collection
- [ ] Configure Prometheus to scrape service metrics endpoints
- [ ] Define counter metrics for each service:
  - `ingestion_requests_total`
  - `kafka_messages_total{topic="..."}`
  - `writer_upserts_total`
- [ ] Set up proper scrape intervals and timeouts

### 2. Service Metrics Implementation
- [ ] **Ingestion Service**: Expose `/metrics` with request counters
- [ ] **Miner Service**: Export Kafka consumer metrics by topic
- [ ] **Analyzer Service**: Export processing and Weaviate operation metrics
- [ ] **Writer Service**: Export Dgraph upsert counters and error rates
- [ ] **Reporting Service**: Export report generation metrics

### 3. Loki Log Aggregation
- [ ] Configure Loki to collect service logs
- [ ] Set up log shipping from all Wave 2 services
- [ ] Implement structured logging with consistent fields:
  - `service`: service name
  - `level`: log level
  - `operation`: operation being performed
  - `repo`: repository (when applicable)
  - `duration_ms`: operation duration

### 4. Grafana Dashboard Creation
- [ ] Create single dashboard with 3 rows:
  - **Throughput**: Messages/sec by topic, requests/sec by service
  - **Latency**: End-to-end pipeline latency, service response times
  - **Errors**: Non-2xx responses, consumer retry rates, failed operations

### 5. Dashboard Panels
- [ ] **Throughput Row**:
  - Kafka topic message rates
  - Service request throughput
  - Data processing velocity
- [ ] **Latency Row**:
  - Producer to writer wall time
  - Service response time percentiles
  - End-to-end pipeline duration
- [ ] **Errors Row**:
  - HTTP error rates by service
  - Kafka consumer error counts
  - Failed operation counters

## Metrics Specification

### Prometheus Counters
```prometheus
# Ingestion service requests
ingestion_requests_total{status="success"} 150
ingestion_requests_total{status="error"} 3

# Kafka messages by topic
kafka_messages_total{topic="repos.ingested", status="produced"} 25
kafka_messages_total{topic="code.mined", status="consumed"} 120
kafka_messages_total{topic="code.analyzed", status="produced"} 95

# Writer upserts
writer_upserts_total{operation="success"} 85
writer_upserts_total{operation="failed"} 2
```

### Grafana Dashboard JSON Structure
- 3 rows with multiple panels each
- Time range: Last 1 hour (configurable)
- Refresh interval: 30 seconds
- Panels showing real-time metrics during DAG execution

## Acceptance Criteria

- [ ] Grafana dashboard shows non-zero throughput during DAG runs
- [ ] No error spikes visible on dashboard during normal operation
- [ ] Loki shows structured logs from all services
- [ ] Prometheus metrics available at `:9090` with proper scraping
- [ ] Dashboard accessible at `:3000` with all panels functional

## Dependencies
- Prometheus server configured and running
- Loki log aggregation configured
- Grafana with proper data sources
- All Wave 2 services exposing `/metrics` endpoints

## Risk Mitigation
- Ensure metrics don't impact service performance
- Implement proper error handling for metrics collection failures
- Use efficient log shipping to avoid resource overhead