from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from datetime import datetime, timedelta
import requests
import pandas as pd
from minio import Minio
from minio.error import S3Error

# Define default arguments
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2023, 1, 1),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# Define the DAG
dag = DAG(
    'fetch_transportation_data_and_store_minio',
    default_args=default_args,
    description='Fetch data from Transportation API and store it in MinIO',
    schedule_interval=None,  # Use None for manual trigger
)

def fetch_data_from_api(**kwargs):
    try:
        url = "https://data.transportation.gov/api/views/keg4-3bc2/rows.csv?accessType=DOWNLOAD"
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for HTTP errors
        
        # Read CSV data
        df = pd.read_csv(url)
        print("Data fetched from API:")
        print(df.head())
        
        # Convert DataFrame to CSV string
        csv_data = df.to_csv(index=False)
        
        # Save the data to XCom for use in the next task
        kwargs['ti'].xcom_push(key='csv_data', value=csv_data)
    except Exception as e:
        print("Error in fetch_data_from_api:", e)

def store_data_in_minio(**kwargs):
    try:
        # Retrieve data from XCom
        csv_data = kwargs['ti'].xcom_pull(key='csv_data')
        print("Data fetched from XCom:", csv_data[:500])  # Print first 500 characters for inspection
        
        # Initialize the MinIO client
        minio_client = Minio(
            'minio:9000',  # Replace with your MinIO server address
            access_key='ROOTUSER',  # Replace with your MinIO access key
            secret_key='CHANGEME123',  # Replace with your MinIO secret key
            secure=False  # Set secure to False for HTTP
        )
        print("MinIO client initialized")
        
        # Create the bucket if it doesn't exist
        bucket_name = 'testbucket'
        if not minio_client.bucket_exists(bucket_name):
            minio_client.make_bucket(bucket_name)
        print(f"Bucket '{bucket_name}' is ready")

        # Save data to a temporary file
        file_path = '/tmp/api_data.csv'
        with open(file_path, 'w') as file:
            file.write(csv_data)
        print(f"Data written to temporary file: {file_path}")
        
        # Upload the file to MinIO
        try:
            minio_client.fput_object(
                bucket_name,
                'transportation_data.csv',
                file_path
            )
            print("File successfully uploaded to MinIO")
        except S3Error as e:
            print("Error occurred while uploading to MinIO:", e)
    except Exception as e:
        print("Error in store_data_in_minio:", e)

# Define the tasks
fetch_data_task = PythonOperator(
    task_id='fetch_data_from_api',
    provide_context=True,
    python_callable=fetch_data_from_api,
    dag=dag,
)

store_data_task = PythonOperator(
    task_id='store_data_in_minio',
    provide_context=True,
    python_callable=store_data_in_minio,
    dag=dag,
)

# Set task dependencies
fetch_data_task >> store_data_task
