# FreshPoC Data Flow Pipeline Architecture

## Overview

The data flow pipeline in FreshPoC demonstrates a complete end-to-end data processing workflow from ingestion to reporting. The pipeline is orchestrated by Apache Airflow and uses Kafka for event-driven communication between services.

## Pipeline Stages

### 1. **Ingestion Stage**
**Service**: Ingestion Service (Port: 8011)

**Purpose**: Collect data from external sources and prepare it for processing.

```mermaid
graph LR
    A[External Sources<br/>GitHub, APIs] --> B[Ingestion Service]
    B --> C[Kafka Topic: ingestion_events]
    C --> D[Event: repository_ingested]
```

**Key Operations**:
- Repository cloning and metadata extraction
- Data validation and normalization
- Event publishing to Kafka
- Error handling and retry logic

**API Endpoints**:
- `GET /health` - Health check
- `GET /trigger?repo=<url>` - Trigger ingestion for specific repository

### 2. **Mining Stage**
**Service**: Miner Service (Port: 8012)

**Purpose**: Extract detailed metadata and relationships from ingested data.

```mermaid
graph LR
    A[Kafka: ingestion_events] --> B[Miner Service]
    B --> C[Metadata Extraction]
    C --> D[Relationship Discovery]
    D --> E[Kafka Topic: mining_results]
    E --> F[Event: metadata_extracted]
```

**Key Operations**:
- Event consumption from Kafka
- Code analysis and dependency extraction
- Metadata enrichment and classification
- Structured data publishing

### 3. **Analysis Stage**
**Service**: Analyzer Service (Port: 8013)

**Purpose**: Perform advanced analysis on mined data to generate insights.

```mermaid
graph LR
    A[Kafka: mining_results] --> B[Analyzer Service]
    B --> C[Pattern Recognition]
    C --> D[Insight Generation]
    D --> E[Anomaly Detection]
    E --> F[Kafka Topic: analysis_complete]
    F --> G[Event: analysis_finished]
```

**Key Operations**:
- Statistical analysis and trend detection
- Quality metrics calculation
- Risk assessment and recommendations
- Analysis result publishing

### 4. **Writing Stage**
**Service**: Writer Service (Port: 8014)

**Purpose**: Persist processed data to the graph database using Dgraph.

```mermaid
graph LR
    A[Kafka: analysis_complete] --> B[Writer Service]
    B --> C[Dgraph Schema Management]
    C --> D[Node Creation]
    D --> E[Edge Creation]
    E --> F[Relationship Mapping]
    F --> G[Dgraph Graph Storage]
```

**Key Operations**:
- Graph schema definition and updates
- Node and relationship creation via HTTP API
- Data validation and conflict resolution
- Transaction management with commitNow

**Dgraph Integration**:
```json
{
  "schema": "name: string @index(term) . repo: string @index(exact) .",
  "mutations": {
    "set": [
      {"repo": "jaffle-shop-classic"},
      {"name": "demo-user", "repo": "jaffle-shop-classic"}
    ]
  },
  "commitNow": true
}
```

### 5. **Query Stage**
**Service**: Query API Service (Port: 8015)

**Purpose**: Provide GraphQL query interface to the knowledge graph.

```mermaid
graph LR
    A[Client Applications] --> B[Query API Service]
    B --> C[GraphQL Query Processing]
    C --> D[Dgraph Query Engine]
    D --> E[Result Filtering]
    E --> F[Response Formatting]
    F --> G[JSON Response]
```

**Key Operations**:
- GraphQL query parsing and validation
- Query optimization and execution
- Result pagination and filtering
- Response formatting and caching

**Sample Query**:
```graphql
{
  all(func: has(repo)) {
    uid
    repo
    name
  }
}
```

### 6. **Reporting Stage**
**Service**: Reporting Service (Port: 8016)

**Purpose**: Generate human-readable reports with visualizations.

```mermaid
graph LR
    A[Scheduled/Automatic] --> B[Reporting Service]
    B --> C[Dgraph Data Query]
    C --> D[Report Generation]
    D --> E[Mermaid Diagram Creation]
    E --> F[Markdown Formatting]
    F --> G[MinIO Storage]
    G --> H[Report Available]
```

**Key Operations**:
- Automated report scheduling
- Graph data aggregation and analysis
- Mermaid diagram generation
- Multi-format report creation
- Artifact storage and versioning

## End-to-End Sequence Flow

```mermaid
sequenceDiagram
    participant U as User/Admin
    participant A as Airflow Scheduler
    participant I as Ingestion
    participant K as Kafka
    participant M as Miner
    participant Z as Analyzer
    participant W as Writer
    participant D as Dgraph
    participant Q as Query API
    participant R as Reporting
    participant S as MinIO

    Note over U,A: DAG Execution Triggered

    A->>I: Execute ingestion task
    activate I
    I->>K: Publish repository_ingested event
    I->>A: Task completed
    deactivate I

    A->>M: Execute miner task
    activate M
    M->>K: Consume ingestion_events
    M->>K: Publish metadata_extracted event
    M->>A: Task completed
    deactivate M

    A->>Z: Execute analyzer task
    activate Z
    Z->>K: Consume mining_results
    Z->>K: Publish analysis_complete event
    Z->>A: Task completed
    deactivate Z

    A->>W: Execute writer task
    activate W
    W->>D: Create/update graph schema
    W->>D: Write nodes and relationships
    W->>A: Task completed
    deactivate W

    A->>R: Execute reporting task
    activate R
    R->>D: Query graph for report data
    R->>S: Generate and upload report
    R->>A: Task completed
    deactivate R

    Note over A,U: DAG Execution Complete
```

## Event-Driven Architecture

### Kafka Topic Structure

| Topic | Purpose | Event Types |
|-------|---------|-------------|
| **ingestion_events** | Repository ingestion notifications | `repository_ingested`, `ingestion_failed` |
| **mining_results** | Metadata extraction results | `metadata_extracted`, `mining_error` |
| **analysis_complete** | Analysis insights and findings | `analysis_finished`, `analysis_error` |
| **system_events** | System-wide notifications | `service_started`, `health_check_failed` |

### Event Schema

```json
{
  "event_id": "uuid",
  "event_type": "repository_ingested",
  "timestamp": "2025-10-04T20:40:00Z",
  "source": "ingestion_service",
  "data": {
    "repository": {
      "url": "https://github.com/dbt-labs/jaffle-shop-classic",
      "name": "jaffle-shop-classic",
      "metadata": {...}
    }
  },
  "correlation_id": "dag_run_id"
}
```

## Data Transformation Pipeline

### Data Quality Gates

1. **Ingestion Validation**
   - Source accessibility check
   - Data format validation
   - Size and complexity assessment

2. **Mining Quality**
   - Metadata completeness verification
   - Relationship consistency checks
   - Error rate monitoring

3. **Analysis Validation**
   - Statistical significance testing
   - Insight quality scoring
   - Anomaly detection thresholds

### Error Handling

```mermaid
graph TD
    A[Task Execution] --> B{Health Check}
    B -->|Pass| C[Continue Pipeline]
    B -->|Fail| D[Retry Logic]
    D --> E{Max Retries?}
    E -->|No| A
    E -->|Yes| F[Error Event]
    F --> G[Kafka Dead Letter Topic]
    G --> H[Monitoring Alert]
```

## Performance Considerations

### Bottleneck Analysis

| Stage | Potential Bottleneck | Mitigation |
|-------|---------------------|------------|
| **Ingestion** | Network I/O, large repos | Async processing, batching |
| **Mining** | CPU-intensive parsing | Parallel processing, caching |
| **Writing** | Graph database writes | Batch mutations, connection pooling |
| **Reporting** | Large graph traversals | Query optimization, pagination |

### Monitoring Points

- **Throughput**: Events per second at each stage
- **Latency**: Processing time for individual items
- **Error Rates**: Failed operations and retries
- **Data Quality**: Completeness and accuracy metrics

## Integration Patterns

### Service Communication

1. **Synchronous**: HTTP REST APIs for control operations
2. **Asynchronous**: Kafka events for data processing
3. **Batch**: MinIO for report and artifact storage

### Data Consistency

- **Eventual Consistency**: Across distributed services
- **Transaction Boundaries**: Within individual service operations
- **Idempotency**: Event replay protection with correlation IDs

## Testing Strategy

### Pipeline Testing

```mermaid
graph LR
    A[Unit Tests] --> B[Service Integration]
    B --> C[End-to-End Pipeline]
    C --> D[Performance Tests]
    D --> E[Chaos Engineering]
```

### Test Data Flow

1. **Mock external sources** for ingestion testing
2. **Synthetic events** for pipeline component testing
3. **Golden datasets** for report validation
4. **Load testing** for performance validation

This data flow architecture ensures reliable, scalable, and maintainable data processing while providing comprehensive observability into the entire pipeline lifecycle.
