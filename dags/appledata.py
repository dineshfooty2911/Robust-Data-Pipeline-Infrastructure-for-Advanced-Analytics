from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from datetime import datetime, timedelta
import pandas as pd
import os
from minio import Minio
from minio.error import S3Error
from kaggle.api.kaggle_api_extended import KaggleApi
import json

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
    'fetch_kaggle_data_and_store_minio',
    default_args=default_args,
    description='Fetch data from Kaggle, unzip, and store in MinIO',
    schedule_interval=None,  # Use None for manual trigger
)

def fetch_data_from_kaggle(**kwargs):
    try:
        # Create a directory for Kaggle credentials
        kaggle_dir = '/usr/local/airflow/kaggle'
        os.makedirs(kaggle_dir, exist_ok=True)
        
        # Write kaggle.json file dynamically
        kaggle_credentials = {
            "username": "dineshfooty29",
            "key": "0c28f9d79e4c983950bcd9bcf3400d2e"
        }
        kaggle_json_path = os.path.join(kaggle_dir, 'kaggle.json')
        with open(kaggle_json_path, 'w') as f:
            json.dump(kaggle_credentials, f)
        
        # Set permissions for the kaggle.json file
        os.chmod(kaggle_json_path, 0o600)
        
        # Set environment variable for Kaggle config directory
        os.environ['KAGGLE_CONFIG_DIR'] = kaggle_dir
        
        # Initialize and authenticate the Kaggle API
        api = KaggleApi()
        api.authenticate()

        # Download dataset from Kaggle
        api.dataset_download_files('nikhil1e9/netflix-stock-price', path='/tmp', unzip=True)
        print("Dataset downloaded and unzipped")

        # Find the extracted CSV file
        extracted_csv_file = [f for f in os.listdir('/tmp') if f.endswith('.csv')][0]
        extracted_csv_path = os.path.join('/tmp', extracted_csv_file)
        
        # Read the extracted CSV data
        df = pd.read_csv(extracted_csv_path)
        print("Data extracted from CSV:")
        print(df.head())
        
        # Convert DataFrame to CSV string
        csv_data = df.to_csv(index=False)
        
        # Save the data to XCom for use in the next task
        kwargs['ti'].xcom_push(key='csv_data', value=csv_data)
    except Exception as e:
        print("Error in fetch_data_from_kaggle:", e)

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
                'netflix_stock_data.csv',
                file_path
            )
            print("File successfully uploaded to MinIO")
        except S3Error as e:
            print("Error occurred while uploading to MinIO:", e)
    except Exception as e:
        print("Error in store_data_in_minio:", e)

# Define the tasks
fetch_data_task = PythonOperator(
    task_id='fetch_data_from_kaggle',
    provide_context=True,
    python_callable=fetch_data_from_kaggle,
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
