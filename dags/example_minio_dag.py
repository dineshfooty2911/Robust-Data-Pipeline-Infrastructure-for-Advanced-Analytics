from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.providers.amazon.aws.hooks.s3 import S3Hook
from datetime import datetime, timedelta
import requests
import json

# Default arguments for the DAG
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2023, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# Create the DAG
dag = DAG(
    'example_minio_dag',
    default_args=default_args,
    description='A simple tutorial DAG to fetch data and store in MinIO',
    schedule_interval=timedelta(days=1),
)

def fetch_data_from_api():
    url = "https://jsonplaceholder.typicode.com/todos/1"
    response = requests.get(url)
    data = response.json()
    return data

def store_data_in_minio(**context):
    # Fetch the API response from XCom
    data = context['task_instance'].xcom_pull(task_ids='fetch_data')
    data_str = json.dumps(data)

    # Use S3Hook to interact with MinIO
    hook = S3Hook(aws_conn_id='minio_conn')
    hook.load_string(
        string_data=data_str,
        key='data/todo.json',
        bucket_name='my-bucket',
        replace=True
    )

fetch_data = PythonOperator(
    task_id='fetch_data',
    python_callable=fetch_data_from_api,
    dag=dag,
)

store_data = PythonOperator(
    task_id='store_data',
    python_callable=store_data_in_minio,
    provide_context=True,
    dag=dag,
)

fetch_data >> store_data
