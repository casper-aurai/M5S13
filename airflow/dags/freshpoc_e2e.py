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
    schedule=None,
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

    ingestion >> mining >> analyzing >> writing >> reporting
