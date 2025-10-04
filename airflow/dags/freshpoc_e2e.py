"""
FreshPOC End-to-End DAG

This DAG orchestrates the complete FreshPOC data processing pipeline:
1. Ingestion - Collect and ingest data
2. Mining - Extract insights and patterns
3. Analysis - Process and analyze data
4. Embedding - Generate vector embeddings
5. Writing - Store processed data
6. Query API - Make data available for querying
7. Reporting - Generate reports and visualizations

Each step includes proper error handling and monitoring.
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.operators.dummy import DummyOperator
import logging
import requests
import json

# Default arguments for the DAG
default_args = {
    'owner': 'freshpoc-team',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
}

# Create the DAG
dag = DAG(
    'freshpoc_e2e',
    default_args=default_args,
    description='FreshPOC end-to-end data processing pipeline',
    schedule_interval=timedelta(days=1),  # Run daily
    catchup=False,
    max_active_runs=1,
    tags=['freshpoc', 'e2e', 'pipeline'],
)

def check_service_health(service_name: str, service_url: str) -> bool:
    """Check if a service is healthy."""
    try:
        response = requests.get(f"{service_url}/health", timeout=10)
        if response.status_code == 200:
            health_data = response.json()
            logging.info(f"{service_name} health check passed: {health_data}")
            return True
        else:
            logging.error(f"{service_name} health check failed: HTTP {response.status_code}")
            return False
    except Exception as e:
        logging.error(f"{service_name} health check error: {str(e)}")
        return False

def trigger_service(service_name: str, service_url: str, trigger_data: dict = None) -> dict:
    """Trigger a service endpoint."""
    try:
        response = requests.post(
            f"{service_url}/trigger",
            json=trigger_data or {},
            timeout=30
        )

        if response.status_code in [200, 201, 202]:
            result = response.json()
            logging.info(f"{service_name} trigger successful: {result}")
            return result
        else:
            logging.error(f"{service_name} trigger failed: HTTP {response.status_code}")
            raise Exception(f"Service {service_name} trigger failed")

    except Exception as e:
        logging.error(f"{service_name} trigger error: {str(e)}")
        raise

# ========================================
# TASK DEFINITIONS
# ========================================

def health_check_ingestion():
    """Check ingestion service health."""
    return check_service_health("Ingestion", "http://ingestion:8080")

def health_check_miner():
    """Check miner service health."""
    return check_service_health("Miner", "http://miner:8080")

def health_check_analyzer():
    """Check analyzer service health."""
    return check_service_health("Analyzer", "http://analyzer:8080")

def health_check_embedder():
    """Check embedder service health."""
    return check_service_health("Embedder", "http://embedder:8080")

def health_check_writer():
    """Check writer service health."""
    return check_service_health("Writer", "http://writer:8080")

def health_check_query_api():
    """Check query API service health."""
    return check_service_health("Query API", "http://query-api:8080")

def trigger_ingestion():
    """Trigger data ingestion."""
    return trigger_service(
        "Ingestion",
        "http://ingestion:8080",
        {
            "source": "airflow_dag",
            "batch_id": "{{ ds }}",
            "pipeline_run_id": "{{ run_id }}"
        }
    )

def trigger_mining():
    """Trigger data mining."""
    return trigger_service(
        "Miner",
        "http://miner:8080",
        {
            "batch_id": "{{ ds }}",
            "operation": "mine_patterns"
        }
    )

def trigger_analysis():
    """Trigger data analysis."""
    return trigger_service(
        "Analyzer",
        "http://analyzer:8080",
        {
            "batch_id": "{{ ds }}",
            "analysis_type": "comprehensive"
        }
    )

def trigger_embedding():
    """Trigger vector embedding generation."""
    return trigger_service(
        "Embedder",
        "http://embedder:8080",
        {
            "batch_id": "{{ ds }}",
            "model": "default_embedding_model"
        }
    )

def trigger_writing():
    """Trigger data writing/storage."""
    return trigger_service(
        "Writer",
        "http://writer:8080",
        {
            "batch_id": "{{ ds }}",
            "targets": ["dgraph", "weaviate"]
        }
    )

def trigger_query_api():
    """Trigger query API refresh."""
    return trigger_service(
        "Query API",
        "http://query-api:8080",
        {
            "batch_id": "{{ ds }}",
            "refresh_type": "incremental"
        }
    )

def generate_reports():
    """Generate final reports."""
    return trigger_service(
        "Reporting",
        "http://reporting:8080",
        {
            "batch_id": "{{ ds }}",
            "report_types": ["summary", "detailed", "trends"]
        }
    )

def pipeline_cleanup():
    """Clean up temporary files and resources."""
    logging.info("Performing pipeline cleanup")
    # In a real implementation, this would clean up temporary files,
    # update pipeline status, send notifications, etc.
    return {"status": "completed", "cleanup": "successful"}

# ========================================
# DAG STRUCTURE
# ========================================

# Start and end markers
start_pipeline = DummyOperator(
    task_id='start_pipeline',
    dag=dag,
)

end_pipeline = DummyOperator(
    task_id='end_pipeline',
    dag=dag,
)

# Health checks (run in parallel)
health_checks = [
    PythonOperator(
        task_id=f'health_check_{service}',
        python_callable=globals()[f'health_check_{service}'],
        dag=dag,
    )
    for service in ['ingestion', 'miner', 'analyzer', 'embedder', 'writer', 'query_api']
]

# Pipeline stages
trigger_ingestion_task = PythonOperator(
    task_id='trigger_ingestion',
    python_callable=trigger_ingestion,
    dag=dag,
)

trigger_mining_task = PythonOperator(
    task_id='trigger_mining',
    python_callable=trigger_mining,
    dag=dag,
)

trigger_analysis_task = PythonOperator(
    task_id='trigger_analysis',
    python_callable=trigger_analysis,
    dag=dag,
)

trigger_embedding_task = PythonOperator(
    task_id='trigger_embedding',
    python_callable=trigger_embedding,
    dag=dag,
)

trigger_writing_task = PythonOperator(
    task_id='trigger_writing',
    python_callable=trigger_writing,
    dag=dag,
)

trigger_query_api_task = PythonOperator(
    task_id='trigger_query_api',
    python_callable=trigger_query_api,
    dag=dag,
)

generate_reports_task = PythonOperator(
    task_id='generate_reports',
    python_callable=generate_reports,
    dag=dag,
)

cleanup_task = PythonOperator(
    task_id='pipeline_cleanup',
    python_callable=pipeline_cleanup,
    dag=dag,
)

# ========================================
# DAG DEPENDENCIES
# ========================================

# All health checks must pass before starting
start_pipeline >> health_checks

# Run all health checks in parallel
for health_check in health_checks:
    start_pipeline >> health_check

# Sequential pipeline execution
for i, task in enumerate([
    trigger_ingestion_task,
    trigger_mining_task,
    trigger_analysis_task,
    trigger_embedding_task,
    trigger_writing_task,
    trigger_query_api_task,
    generate_reports_task
]):
    if i == 0:
        # First task depends on all health checks
        for health_check in health_checks:
            health_check >> task
    else:
        # Subsequent tasks depend on previous task
        [health_checks, trigger_ingestion_task, trigger_mining_task,
         trigger_analysis_task, trigger_embedding_task, trigger_writing_task,
         trigger_query_api_task, generate_reports_task][i-1] >> task

# Final cleanup
generate_reports_task >> cleanup_task >> end_pipeline

# All tasks should complete before ending
for task in [trigger_ingestion_task, trigger_mining_task, trigger_analysis_task,
             trigger_embedding_task, trigger_writing_task, trigger_query_api_task,
             generate_reports_task, cleanup_task]:
    task >> end_pipeline
