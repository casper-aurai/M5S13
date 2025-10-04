# [WAVE2-D] Airflow DAG - Real End-to-End Implementation

**Labels:** `airflow`, `p1-high`, `wave2-poc`, `ready-for-dev`

## Objective
Replace DAG stubs with real HTTP calls and Kafka topic polling to create a fully functional end-to-end pipeline.

## Background
Current DAG uses placeholder operators. Need to implement actual service integration with proper error handling and status checking.

## Tasks

### 1. DAG Structure Updates
- [ ] Replace stub operators with real implementations
- [ ] Add proper parameter passing (repo URL)
- [ ] Implement sequential task dependencies
- [ ] Add timeout and retry configurations

### 2. Service Integration Points
- [ ] **IngestionTrigger**: HTTP POST to `/ingestion/trigger?repo=...`
- [ ] **WaitMined**: Poll Kafka `code.mined` topic for messages
- [ ] **WaitAnalyzed**: Poll Kafka `code.analyzed` topic for messages
- [ ] **WriterApply**: Ensure `/writer/stats` counter increases
- [ ] **ReportGenerate**: HTTP GET to `/reporting/generate`

### 3. Task Implementation Details

#### IngestionTrigger
- [ ] Make HTTP call to ingestion service
- [ ] Pass repo URL as DAG parameter
- [ ] Handle HTTP errors appropriately

#### WaitMined
- [ ] Poll `code.mined` topic for at least 1 message
- [ ] Timeout after 60 seconds
- [ ] Extract repo identifier for correlation

#### WaitAnalyzed
- [ ] Poll `code.analyzed` topic for matching messages
- [ ] Correlate with original repo parameter
- [ ] Timeout after 60 seconds

#### WriterApply
- [ ] Poll `/writer/stats` endpoint
- [ ] Verify counter has incremented since DAG start
- [ ] Handle case where no new data is processed

#### ReportGenerate
- [ ] Call `/reporting/generate` endpoint
- [ ] Verify report generation completes successfully

### 4. Configuration & Parameters
- [ ] Add DAG parameter: `repo=https://github.com/dbt-labs/jaffle-shop-classic`
- [ ] Configurable timeouts for wait operations
- [ ] Error handling for failed service calls

## DAG Run Example

```python
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.http import SimpleHttpOperator
from airflow.operators.bash import BashOperator
from airflow.sensors.bash import BashSensor

default_args = {
    'owner': 'data-team',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'wave2_e2e_pipeline',
    default_args=default_args,
    description='Complete Wave 2 E2E pipeline',
    schedule_interval=None,
    catchup=False,
    params={
        "repo": "https://github.com/dbt-labs/jaffle-shop-classic"
    }
)

# Task definitions would go here...
```

## Acceptance Criteria

- [ ] DAG run completes successfully (green status)
- [ ] `reports/latest.md` updated in MinIO after DAG completion
- [ ] Dgraph shows new nodes from the processed repository
- [ ] All intermediate Kafka topics show message flow
- [ ] No task failures or timeouts in normal operation

## Dependencies
- All Wave 2 services running (ingestion, miner, analyzer, writer, reporting)
- Kafka topics created and accessible
- MinIO configured and accessible
- Airflow configured with proper connections

## Risk Mitigation
- If Airflow container on ARM is slow, enable LocalExecutor
- Implement proper error handling and alerting
- Add monitoring for long-running tasks