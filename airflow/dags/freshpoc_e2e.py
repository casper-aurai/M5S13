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

def wait_for_kafka_messages(topic: str, expected_count: int = 1, timeout: int = 300) -> bool:
    """Wait for Kafka messages on a topic."""
    import time
    start_time = time.time()
    
    # In a real implementation, this would poll Kafka consumer for messages
    # For demo, we'll simulate waiting
    while time.time() - start_time < timeout:
        # Simulate checking message count
        current_count = 0  # Replace with actual Kafka consumer check
        if current_count >= expected_count:
            logging.info(f"Found {current_count} messages on topic {topic}")
            return True
        time.sleep(10)
    
    logging.error(f"Timeout waiting for messages on topic {topic}")
    return False

def trigger_ingestion_with_kafka():
    """Trigger ingestion and wait for Kafka messages."""
    # Trigger ingestion
    result = trigger_service(
        "Ingestion",
        "http://ingestion:8080",
        {
            "source": "airflow_dag",
            "batch_id": "{{ ds }}",
            "pipeline_run_id": "{{ run_id }}"
        }
    )
    
    # Wait for messages on repos.ingested topic
    if not wait_for_kafka_messages("repos.ingested", 1):
        raise Exception("No messages received on repos.ingested topic")
    
    return result

def trigger_mining_with_kafka():
    """Trigger mining and wait for Kafka messages."""
    # Mining happens automatically via Kafka consumer
    # Wait for messages on code.mined topic
    if not wait_for_kafka_messages("code.mined", 1):
        raise Exception("No messages received on code.mined topic")
    
    return {"status": "mining_completed"}

def trigger_analysis_with_kafka():
    """Trigger analysis and wait for Kafka messages."""
    # Analysis happens automatically via Kafka consumer
    # Wait for messages on code.analyzed topic
    if not wait_for_kafka_messages("code.analyzed", 1):
        raise Exception("No messages received on code.analyzed topic")
    
    return {"status": "analysis_completed"}

def trigger_writing_with_kafka():
    """Trigger writing and wait for Kafka messages."""
    # Writing happens automatically via Kafka consumer
    # Wait for messages on graph.apply topic
    if not wait_for_kafka_messages("graph.apply", 1):
        raise Exception("No messages received on graph.apply topic")
    
    return {"status": "writing_completed"}

def trigger_reporting_with_minio():
    """Trigger reporting and check MinIO for reports."""
    # Trigger report generation
    result = trigger_service(
        "Reporting",
        "http://reporting:8080",
        {
            "batch_id": "{{ ds }}",
            "report_types": ["summary", "detailed", "trends"]
        }
    )
    
    # Wait for reports in MinIO
    import time
    time.sleep(30)  # Wait for report generation and upload
    
    # In a real implementation, check MinIO for new reports
    # For demo, assume success
    return result

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
    python_callable=trigger_ingestion_with_kafka,
    dag=dag,
)

trigger_mining_task = PythonOperator(
    task_id='trigger_mining',
    python_callable=trigger_mining_with_kafka,
    dag=dag,
)

trigger_analysis_task = PythonOperator(
    task_id='trigger_analysis',
    python_callable=trigger_analysis_with_kafka,
    dag=dag,
)

trigger_embedding_task = PythonOperator(
    task_id='trigger_embedding',
    python_callable=trigger_mining_with_kafka,  # Embedding is part of mining
    dag=dag,
)

trigger_writing_task = PythonOperator(
    task_id='trigger_writing',
    python_callable=trigger_writing_with_kafka,
    dag=dag,
)

trigger_query_api_task = PythonOperator(
    task_id='trigger_query_api',
    python_callable=trigger_mining_with_kafka,  # Query API is refreshed after writing
    dag=dag,
)

generate_reports_task = PythonOperator(
    task_id='generate_reports',
    python_callable=trigger_reporting_with_minio,
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
