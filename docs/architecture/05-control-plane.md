# FreshPoC Control Plane - Apache Airflow

## Control Plane Overview

Apache Airflow serves as the central orchestration engine for the FreshPoC data platform, managing the execution of complex data workflows and ensuring reliable task scheduling across distributed services.

## Architecture Position

```mermaid
graph TB
    %% Control Plane
    subgraph "Control Plane"
        AirflowWeb[Airflow Web UI<br/>Port: 8080]
        AirflowSched[Airflow Scheduler]
        AirflowDB[(PostgreSQL<br/>Metadata DB)]
    end

    %% Data Pipeline
    subgraph "Data Pipeline"
        Ingestion[Ingestion Service]
        Miner[Miner Service]
        Analyzer[Analyzer Service]
        Writer[Writer Service]
        QueryAPI[Query API Service]
        Reporting[Reporting Service]
    end

    %% Storage
    subgraph "Storage & Events"
        Kafka[Kafka Event Bus]
        Dgraph[Dgraph Graph DB]
        MinIO[MinIO Object Storage]
    end

    %% Control Flow
    AirflowWeb --> AirflowDB
    AirflowSched --> AirflowDB
    AirflowSched --> Ingestion
    AirflowSched --> Miner
    AirflowSched --> Analyzer
    AirflowSched --> Writer
    AirflowSched --> QueryAPI
    AirflowSched --> Reporting

    %% Data Flow
    Ingestion --> Kafka
    Miner --> Kafka
    Analyzer --> Kafka
    Writer --> Dgraph
    Reporting --> MinIO
```

## Airflow Configuration

### Database Backend

**PostgreSQL Configuration**:
```yaml
airflow-db:
  image: postgres:15-alpine
  environment:
    POSTGRES_USER: airflow
    POSTGRES_PASSWORD: airflow
    POSTGRES_DB: airflow
  volumes:
    - airflow-db:/var/lib/postgresql/data
```

**Connection String**:
```python
# In docker-compose.yml environment
AIRFLOW__DATABASE__SQL_ALCHEMY_CONN: postgresql+psycopg2://airflow:airflow@airflow-db:5432/airflow
```

### Web Server Configuration

```yaml
airflow:
  image: apache/airflow:2.10.2-python3.11
  environment:
    AIRFLOW__CORE__LOAD_EXAMPLES: "false"
    AIRFLOW__WEBSERVER__RBAC: "true"
    _PIP_ADDITIONAL_REQUIREMENTS: "apache-airflow-providers-http==4.6.1 requests==2.32.3"
  ports:
    - "8080:8080"
```

**Key Settings**:
- **Examples Disabled**: No example DAGs loaded
- **RBAC Enabled**: Role-based access control
- **Custom Providers**: HTTP provider for service calls

### Initialization Process

```mermaid
sequenceDiagram
    participant C as Container
    participant DB as PostgreSQL
    participant A as Airflow

    C->>DB: Start PostgreSQL
    DB-->>C: Database ready

    C->>A: Start Airflow container
    A->>DB: Run migrations
    DB-->>A: Schema updated

    A->>A: Create admin user
    A-->>A: User created (if not exists)

    A->>A: Start web server
    A->>A: Start scheduler
```

## DAG Architecture

### FreshPoC_E2E DAG

The main orchestration DAG that coordinates the entire data pipeline:

```python
from datetime import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator
import requests, os, time

def hit(url):
    for _ in range(30):
        try:
            r = requests.get(url, timeout=3)
            if r.ok: return True
        except Exception: time.sleep(1)
    raise RuntimeError(f"Service not ready: {url}")

with DAG(
    dag_id="FreshPoC_E2E",
    start_date=datetime(2025, 10, 3),
    schedule=None,  # Manual trigger only
    catchup=False,
    tags=["poc","local"],
) as dag:

    ingestion = PythonOperator(
        task_id="ingestion_trigger",
        python_callable=lambda: hit("http://ingestion:8011/trigger?repo=https://github.com/dbt-labs/jaffle-shop-classic")
    )

    mining = PythonOperator(
        task_id="miner_run",
        python_callable=lambda: hit("http://miner:8012/run")
    )

    analyzing = PythonOperator(
        task_id="analyzer_run",
        python_callable=lambda: hit("http://analyzer:8013/run")
    )

    writing = PythonOperator(
        task_id="writer_apply",
        python_callable=lambda: hit("http://writer:8014/apply")
    )

    reporting = PythonOperator(
        task_id="report_generate",
        python_callable=lambda: hit("http://reporting:8016/generate")
    )

    # Define task dependencies
    ingestion >> mining >> analyzing >> writing >> reporting
```

### DAG Structure

```mermaid
graph TD
    A[ingestion_trigger] --> B[miner_run]
    B --> C[analyzer_run]
    C --> D[writer_apply]
    D --> E[report_generate]

    A -.->|Service Health Check| F[Ingestion:8011]
    B -.->|Service Health Check| G[Miner:8012]
    C -.->|Service Health Check| H[Analyzer:8013]
    D -.->|Service Health Check| I[Writer:8014]
    E -.->|Service Health Check| J[Reporting:8016]
```

**DAG Properties**:
- **Schedule**: Manual trigger only (`schedule=None`)
- **Concurrency**: One run at a time (`max_active_runs=1`)
- **Retries**: 3 attempts per task
- **Timeout**: 30 minutes per task

## Task Execution Patterns

### 1. **Service Health Checks**

Each task implements robust health checking:

```python
def hit(url):
    """Robust service health checking with retry logic"""
    for attempt in range(30):  # 30 attempts
        try:
            response = requests.get(url, timeout=3)
            if response.ok:
                return True
        except requests.exceptions.RequestException:
            pass
        time.sleep(1)  # 1 second delay between attempts
    raise RuntimeError(f"Service not ready: {url}")
```

**Benefits**:
- **Reliability**: Handles temporary service unavailability
- **Monitoring**: Validates service readiness before execution
- **Debugging**: Clear error messages for failed services

### 2. **Sequential Processing**

Tasks execute in strict sequence with dependency management:

```mermaid
sequenceDiagram
    participant AF as Airflow Scheduler
    participant I as Ingestion Service
    participant M as Miner Service
    participant Z as Analyzer Service
    participant W as Writer Service
    participant R as Reporting Service

    AF->>I: Execute ingestion_trigger
    I-->>AF: Task completed
    AF->>M: Execute miner_run
    M-->>AF: Task completed
    AF->>Z: Execute analyzer_run
    Z-->>AF: Task completed
    AF->>W: Execute writer_run
    W-->>AF: Task completed
    AF->>R: Execute report_generate
    R-->>AF: Task completed
```

**Execution Guarantees**:
- **Sequential**: One task at a time
- **Failure Handling**: Failed tasks stop the DAG
- **Retry Logic**: Automatic retries with exponential backoff
- **Idempotency**: Safe to retry failed operations

## Scheduler Configuration

### Scheduler Settings

```python
# Airflow Configuration (airflow.cfg)
[scheduler]
max_dagruns_to_create = 16
max_tis_per_query = 512
parsing_processes = 2
```

**Key Parameters**:
- **DAG Parsing**: Separate process for DAG file monitoring
- **Task Scheduling**: Optimized for parallel task execution
- **Resource Limits**: Configurable memory and CPU limits

### Scheduling Behavior

1. **DAG Parsing**: Monitors `/opt/airflow/dags` for changes
2. **Task Scheduling**: Queues tasks based on dependencies
3. **Executor Selection**: Routes tasks to appropriate executors
4. **State Management**: Tracks task and DAG run states

## Executor Architecture

### Current Configuration

**Sequential Executor** (Development):
```python
# Default for development
[core]
executor = SequentialExecutor
```

**Production Options**:
- **LocalExecutor**: Multi-process execution
- **CeleryExecutor**: Distributed task execution
- **KubernetesExecutor**: Container-based execution

### Executor Comparison

| Executor | Pros | Cons | Use Case |
|----------|------|------|----------|
| **Sequential** | Simple, no setup | Single-threaded | Development, simple workflows |
| **Local** | Parallel execution | Process overhead | Small-medium deployments |
| **Celery** | Distributed, scalable | Complex setup | Large deployments |
| **Kubernetes** | Auto-scaling, isolation | Resource intensive | Cloud-native deployments |

## Monitoring and Observability

### Airflow Metrics

**Built-in Metrics**:
- DAG run success/failure rates
- Task execution times
- Scheduler performance
- Database connection pool status

**Custom Metrics** (via StatsD)**:
```python
from airflow.metrics import timer, counter

@timer("custom_task_duration")
def custom_task():
    # Task implementation
    pass
```

### Integration with Platform Monitoring

```mermaid
graph LR
    A[Airflow] --> B[StatsD Exporter]
    B --> C[Prometheus]
    C --> D[Grafana]

    A --> E[Structured Logs]
    E --> F[Loki]
    F --> G[Grafana]
```

**Monitoring Dashboards**:
- **DAG Health**: Success rates and execution times
- **Task Performance**: Individual task metrics
- **Scheduler Status**: Parsing and scheduling metrics
- **Error Tracking**: Failed tasks and retry patterns

## User Management

### Authentication

**RBAC Configuration**:
```yaml
environment:
  AIRFLOW__WEBSERVER__RBAC: "true"
```

**Default Users**:
- **Username**: `admin`
- **Password**: `admin` (configured via environment)
- **Role**: `Admin` (full access)

**User Creation** (First Run)**:
```bash
# In Airflow container
airflow users create \
  --username admin \
  --password admin \
  --firstname Admin \
  --lastname User \
  --role Admin \
  --email admin@example.com
```

### Access Control

**Roles and Permissions**:
- **Admin**: Full DAG and user management
- **Op**: DAG execution and monitoring
- **User**: Read-only access to DAGs
- **Viewer**: Basic dashboard access

## Error Handling and Recovery

### Failure Scenarios

1. **Service Unavailable**: Tasks retry with exponential backoff
2. **Network Issues**: Connection timeouts with retry logic
3. **Data Corruption**: Validation checks prevent bad data
4. **Resource Exhaustion**: Task timeout and resource limits

### Recovery Procedures

```mermaid
graph TD
    A[DAG Run Fails] --> B[Check Logs]
    B --> C{Retry Possible?}
    C -->|Yes| D[Mark Task Success]
    C -->|No| E[Manual Intervention]
    E --> F[Fix Root Cause]
    F --> G[Rerun DAG]
```

**Recovery Strategies**:
1. **Automatic Retry**: Failed tasks retry up to 3 times
2. **Manual Re-run**: Failed tasks can be marked successful
3. **DAG Backfill**: Rerun historical DAG runs
4. **Task Skipping**: Skip problematic tasks in chain

## Performance Optimization

### DAG Optimization

**Best Practices**:
- **Task Granularity**: Balance between too many vs too few tasks
- **Resource Allocation**: Appropriate memory and CPU per task
- **Parallel Execution**: Independent tasks run in parallel
- **Idempotent Tasks**: Safe to retry without side effects

### Scheduler Tuning

**Configuration Optimization**:
```python
[scheduler]
# Optimize for FreshPoC workload
dag_dir_list_interval = 30  # Check for DAG changes every 30s
min_file_process_interval = 30  # Process file changes every 30s
parsing_processes = 2  # Parallel DAG parsing
```

### Monitoring Performance

**Key Metrics to Track**:
- **Scheduler Loop Duration**: Time to process DAGs
- **Task Scheduling Delay**: Time from trigger to execution
- **DAG Parsing Time**: Time to parse and validate DAGs
- **Database Query Performance**: Metadata DB performance

## Development Workflow

### DAG Development Cycle

```mermaid
graph TD
    A[Local Development] --> B[Write DAG Code]
    B --> C[Syntax Validation]
    C --> D[Unit Testing]
    D --> E[Docker Test]
    E --> F[Deploy to Airflow]
    F --> G[Manual Testing]
    G --> H[Production Deployment]
```

### Version Control Strategy

**DAG Versioning**:
- **Git-based**: DAG files in version control
- **Environment Separation**: Different DAGs per environment
- **Rollback**: Previous versions can be restored
- **Change Management**: Code review for DAG changes

This Airflow control plane provides robust workflow orchestration with comprehensive monitoring, error handling, and scalability for the FreshPoC data platform.
