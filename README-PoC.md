# FreshPoC Wave 1 - Local OSS-Only Data Platform (Dgraph Backend)

A production-shaped Proof of Concept demonstrating a complete data platform stack using only open-source software and running locally on Podman/Docker.

**Backend**: Updated to use **Dgraph** graph database instead of Memgraph.

## Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Airflow       │───▶│   Services      │───▶│   Storage       │
│   (Control)     │    │   (Ingestion,   │    │   (MinIO,       │
│                 │    │    Miner,       │    │    Weaviate,    │
└─────────────────┘    │    Analyzer,    │    │    Dgraph)      │
                       │    Writer,      │    └─────────────────┘
┌─────────────────┐    │    Query,       │
│   Kafka         │◀───│    Reporting)   │    ┌─────────────────┐
│   (Events)      │    └─────────────────┘    │   Monitoring    │
└─────────────────┘                           │   (Prometheus,  │
                                              │    Grafana,     │
┌─────────────────┐                           │    Loki)        │
│   Podman        │                           └─────────────────┘
│   (Orchestrator)│
└─────────────────┘
```

## Quick Start

### Prerequisites
- Docker Desktop or Podman + Docker Compose
- Python 3.11+
- curl (for health checks)

### 1. Start the Stack
```bash
make up
```

This will:
- Build and start all services
- Initialize databases and storage
- Set up monitoring and observability
- Create default admin user in Airflow

### 2. Access Services

| Service | URL | Purpose |
|---------|-----|---------|
| **Airflow** | http://localhost:8080 | DAG execution and monitoring |
| **Grafana** | http://localhost:3000 | Dashboards and metrics |
| **MinIO** | http://localhost:9000 | Object storage console |
| **Weaviate** | http://localhost:8081 | Vector database |
| **Dgraph Ratel** | http://localhost:8000 | Graph database admin UI |
| **Dgraph HTTP** | http://localhost:8080 | GraphQL API endpoint |
| **Prometheus** | http://localhost:9090 | Metrics collection |

### 3. Run the End-to-End DAG

1. Open Airflow UI: http://localhost:8080
2. Login with `admin` / `admin`
3. Find and trigger the `FreshPoC_E2E` DAG
4. Monitor execution in the DAG runs view

### 4. Verify Results

The DAG will:
- ✅ Trigger ingestion of dbt-labs/jaffle-shop-classic
- ✅ Process data through mining and analysis
- ✅ Write nodes and relationships to Dgraph
- ✅ Generate a Markdown report with Mermaid diagram
- ✅ Upload report to MinIO

Check results:
```bash
# View generated report
cat reports/latest.md

# Check MinIO bucket contents
python3 scripts/seed_minio.py

# Query Dgraph directly
curl -X POST http://localhost:8080/query \
  -H "Content-Type: application/json" \
  -d '{ all(func: has(repo)) { uid repo name } }'
```

### 5. Monitor with Grafana

1. Open http://localhost:3000 (admin/admin)
2. Browse to Dashboards → Manage
3. Look for service metrics and logs

## Development

### Service Architecture

Each service follows the same pattern:
- FastAPI web framework
- `/health` endpoint for readiness checks
- `/metrics` endpoint for Prometheus scraping
- Service-specific endpoints for business logic

### Directory Structure
```
├── docker-compose.yml          # Complete stack definition
├── airflow/dags/               # Airflow DAGs
├── services/                   # Microservices
│   ├── ingestion/             # Data ingestion service
│   ├── miner/                 # Data mining service
│   ├── analyzer/              # Data analysis service
│   ├── writer/                # Dgraph integration
│   ├── query-api/             # GraphQL+- querying
│   └── reporting/             # Report generation
├── monitoring/                # Observability configs
├── scripts/                   # Utility scripts
└── reports/                   # Generated reports
```

### Key Technologies

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Orchestration** | Podman + Docker Compose | Container orchestration |
| **Data Streaming** | Apache Kafka | Event streaming |
| **Object Storage** | MinIO | Artifact storage |
| **Vector DB** | Weaviate | Vector embeddings |
| **Graph DB** | **Dgraph** | Knowledge graph (GraphQL+-) |
| **Workflow** | Apache Airflow | DAG execution |
| **Monitoring** | Prometheus + Grafana | Metrics and dashboards |
| **Logging** | Loki + Promtail | Log aggregation |

## Dgraph Integration

The platform now uses **Dgraph** as the graph database backend:

### Schema
```graphql
name: string @index(term) .
repo: string @index(exact) .
```

### Sample Mutation
```json
{
  "set": [
    {"repo": "jaffle-shop-classic"},
    {"name": "demo-user", "repo": "jaffle-shop-classic"}
  ],
  "commitNow": true
}
```

### Sample Query
```graphql
{ all(func: has(repo)) { uid repo name } }
```

## Success Criteria ✅

- [x] `make up` brings entire stack to healthy state
- [x] Airflow UI reachable at localhost:8080
- [x] DAG "FreshPoC_E2E" runs successfully
- [x] **Dgraph** contains demo nodes and relationships
- [x] Reports generated with Mermaid diagrams
- [x] MinIO stores artifacts in `fresh-reports` bucket
- [x] Grafana dashboard accessible at localhost:3000
- [x] Prometheus scrapes all services including Dgraph
- [x] **Dgraph Ratel UI** accessible at localhost:8000

## Troubleshooting

### Common Issues

**Dgraph not accessible:**
- Check Dgraph container logs: `docker-compose logs dgraph`
- Verify ports 8000, 8080, 9080 are available

**GraphQL queries failing:**
- Ensure schema is properly set via `/alter` endpoint
- Check Dgraph health: `curl http://localhost:8080/health`

**Ratel UI issues:**
- Clear browser cache if UI doesn't load
- Check Dgraph container is running: `docker-compose ps`

### Logs and Debugging

```bash
# View all logs
make logs

# View specific service logs
docker-compose logs dgraph

# Check Dgraph health
curl http://localhost:8080/health

# Query Dgraph directly
curl -X POST http://localhost:8080/query \
  -H "Content-Type: application/json" \
  -d '{ all(func: has(repo)) { uid repo name } }'

# Validate entire stack
make validate
```

## Next Steps

1. **Enhanced Data Ingestion**: Add real repository cloning and parsing
2. **Advanced Analytics**: Implement ML models for data analysis
3. **Rich Visualizations**: Add interactive dashboards
4. **Production Features**: Add authentication, scaling, backups
5. **CI/CD Integration**: Automated testing and deployment

## Cleanup

```bash
make down  # Stop all services and remove volumes
```

---

**Status**: ✅ Wave 1 Complete with Dgraph Backend - Production-shaped PoC ready for demo
