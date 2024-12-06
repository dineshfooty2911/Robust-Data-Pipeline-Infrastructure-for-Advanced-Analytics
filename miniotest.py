from minio import Minio
from minio.error import S3Error\

client = Minio(
    "localhost:9000",
    access_key="ROOTUSER",
    secret_key="CHANGEME123",
    secure=False
)

# List all buckets to test the connection
try:
    buckets = client.list_buckets()
    print("Buckets:")
    for bucket in buckets:
        print(bucket.name)
except S3Error as exc:
    print("Error occurred:", exc)