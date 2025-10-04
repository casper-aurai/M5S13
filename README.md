# FreshPOC - Data Processing Platform

FreshPOC is a comprehensive data processing platform designed for intelligent document analysis, vector search, and automated workflow orchestration. Built with modern observability-first principles and containerized microservices architecture.

## 🚀 Quick Start

Get the entire FreshPOC stack running in under 5 minutes!

### Prerequisites

- **Podman** (recommended) or Docker
- **Python 3.8+** for development tools
- **Git** for version control

### 1. Clone and Setup

```bash
git clone https://github.com/casper-aurai/M5S13.git
cd M5S13
```

### 2. Start Infrastructure

```bash
# Initialize Podman machine (first time only)
podman machine init

# Start all services
make up

# Wait for services to be healthy (2-3 minutes)
make health
```

### 3. Verify Services

All services should show as healthy:

```bash
make status
```

### 4. Access Applications

| Service | URL | Credentials |
|---------|-----|-------------|
| **Kafka UI** | http://localhost:8080 | - |
| **Grafana** | http://localhost:3000 | admin/freshpoc-grafana |
| **Airflow** | http://localhost:8083 | - |
| **Dgraph Ratel** | http://localhost:8081 | - |
| **Weaviate** | http://localhost:8082 | - |
| **MinIO Console** | http://localhost:9001 | freshpoc-admin/freshpoc-password |

### 5. Run First Pipeline

Trigger the end-to-end pipeline:

```bash
# Access Airflow UI and manually trigger the "freshpoc_e2e" DAG
# OR trigger a service directly:
curl -X POST http://localhost:8080/trigger \
  -H "Content-Type: application/json" \
  -d '{"source": "manual_test", "batch_id": "test-$(date +%s)"}'
```

## 🏗️ Architecture

FreshPOC follows a microservices architecture with comprehensive observability:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Ingestion     │───▶│     Miner       │───▶│    Analyzer     │
│   Service       │    │   Service       │    │   Service       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Embedder      │    │     Writer      │    │  Query API      │
│   Service       │    │   Service       │    │   Service       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│    Weaviate     │    │     Dgraph      │    │     MinIO       │
│  (Vectors)      │    │   (Graph DB)    │    │  (Storage)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Infrastructure Services

- **Kafka**: Message queuing and event streaming
- **Dgraph**: Graph database for relationship modeling
- **Weaviate**: Vector database for semantic search
- **MinIO**: Object storage for documents and artifacts
- **PostgreSQL**: Metadata storage for Airflow
- **Redis**: Caching and coordination
- **Loki + Promtail**: Log aggregation
- **Prometheus + Grafana**: Metrics and monitoring

## 📊 Monitoring & Observability

FreshPOC is built with observability-first principles:

### Metrics Collection
- **Prometheus** scrapes metrics from all services
- **Grafana** provides dashboards and visualizations
- **Custom metrics** for business logic monitoring

### Logging
- **Structured JSON logging** across all services
- **Loki** for centralized log aggregation and querying
- **Promtail** for log collection from containers

### Health Checks
- **Health endpoints** on all services (`/health`)
- **Automated health verification** in CI/CD
- **Service dependency monitoring**

## 🔧 Development

### Development Tools

The project includes comprehensive development tooling:

```bash
# Start development environment
make up

# View logs from all services
make logs

# Check service health
make health

# View Kafka topics
make topics

# Access service UIs
make kafka-ui    # Kafka management
make grafana     # Monitoring dashboards
make airflow     # Workflow orchestration

# Clean everything (removes all data)
make clean
```

### MCP Integration

This project includes **Model Context Protocol (MCP) servers** for AI-assisted development:

- **Filesystem MCP**: Controlled file operations with sandboxing
- **Git MCP**: Repository operations and management
- **Redis MCP**: State management and coordination
- **Fetch MCP**: Secure HTTP operations for internal services
- **Podman MCP**: Container orchestration
- **Sequential Thinking MCP**: Chain-of-thought guidance
- **Task Master MCP**: Issue and task management
- **HTTP Wrapper MCP**: Secure local HTTP endpoint access

### Code Quality

```bash
# Format code
make format

# Run linting
make lint

# Run tests
make test
```

## 🏭 Services

### Core Services

| Service | Purpose | Technology | Port |
|---------|---------|------------|------|
| **Ingestion** | Data collection and validation | Python/FastAPI | 8080 |
| **Miner** | Pattern extraction and analysis | Python/FastAPI | 8080 |
| **Analyzer** | Data transformation and insights | Python/FastAPI | 8080 |
| **Embedder** | Vector generation and storage | Python/FastAPI | 8080 |
| **Writer** | Data persistence and indexing | Python/FastAPI | 8080 |
| **Query API** | Data retrieval and search | Python/FastAPI | 8080 |
| **Reporting** | Report generation and export | Python/FastAPI | 8080 |

### Infrastructure Services

| Service | Purpose | Technology | Port |
|---------|---------|------------|------|
| **Kafka** | Message queuing | Confluent Kafka | 9092 |
| **Dgraph** | Graph database | Dgraph | 8080 |
| **Weaviate** | Vector database | Weaviate | 8080 |
| **MinIO** | Object storage | MinIO | 9000 |
| **PostgreSQL** | Metadata storage | PostgreSQL | 5432 |
| **Redis** | Caching | Redis | 6379 |
| **Airflow** | Workflow orchestration | Apache Airflow | 8080 |

## 📋 Project Structure

```
repo-root/
│
├─ docker/                 # Podman/Compose definitions
│   └─ docker-compose.yml  # Complete infrastructure stack
│
├─ services/               # Microservices
│   ├─ ingestion/          # Data ingestion service
│   ├─ miner/             # Pattern mining service
│   ├─ analyzer/          # Data analysis service
│   ├─ embedder/          # Vector embedding service
│   ├─ writer/            # Data persistence service
│   ├─ query-api/         # Data access API
│   └─ reporting/         # Report generation service
│
├─ airflow/               # Workflow orchestration
│   ├─ dags/             # Airflow DAGs
│   │   └─ freshpoc_e2e.py # End-to-end pipeline
│   └─ plugins/          # Custom Airflow plugins
│
├─ monitoring/           # Observability stack
│   ├─ prometheus.yml   # Metrics collection config
│   ├─ grafana-provisioning/ # Dashboard definitions
│   └─ promtail.yml     # Log collection config
│
├─ docs/                # Documentation
│   ├─ adr/            # Architecture Decision Records
│   └─ generated/      # Auto-generated docs
│
├─ reports/            # Generated reports
├─ data/              # Local data storage
├─ servers/           # MCP server implementations
└─ .windsurf/        # Windsurf IDE configuration
```

## 🎯 Sprint 1 Goals

**Sprint 1 (1 hour)** focuses on establishing the foundation:

✅ **Infrastructure**: Podman + complete service stack
✅ **Observability**: Prometheus, Grafana, Loki integration
✅ **Orchestration**: Airflow DAG for end-to-end pipeline
✅ **Development Tools**: Makefile, MCP servers, cascade rules
✅ **Documentation**: ADRs, quickstart guide, service documentation

## 📚 Documentation

### Architecture Decision Records (ADRs)
- [ADR-0001: Podman for Container Orchestration](./docs/adr/ADR-0001-podman.md)
- [ADR-0002: Airflow for Workflow Orchestration](./docs/adr/ADR-0002-airflow.md)

### Development Guides
- [MCP Server Documentation](./servers/README.md)
- [Cascade Rules](./.windsurf/cascade-rules.md)
- [Service Development Guide](./docs/service-development.md) *(coming soon)*

## 🤝 Contributing

### Getting Started
1. Follow the [Quick Start](#-quick-start) guide
2. Read the [Cascade Rules](./.windsurf/cascade-rules.md)
3. Create an ADR for any architectural changes
4. Update documentation for new features

### Development Workflow
1. **Create Issue**: Use the MCP Task Master template for new work
2. **Branch**: Create feature branch from main
3. **Develop**: Use MCP servers for code generation and file operations
4. **Test**: Verify services start and pass health checks
5. **Document**: Update README and create ADRs as needed
6. **PR**: Link to relevant issues and ADRs

### Code Standards
- **Python**: Black formatting, type hints, comprehensive error handling
- **Commits**: Conventional commit format with issue/PR references, and land every edit in its own descriptive commit so Cascade/MCP automation can trace task boundaries
- **Tests**: Unit tests for all business logic
- **Documentation**: Update README and docs for user-facing changes

## 📞 Support

- **Issues**: Use GitHub Issues with appropriate labels
- **Discussions**: Use GitHub Discussions for questions and ideas
- **MCP Integration**: Leverage Windsurf MCP servers for development assistance

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

**Built with ❤️ using Podman, Airflow, and comprehensive observability tooling.**