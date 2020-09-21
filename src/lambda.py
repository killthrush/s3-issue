
from s3_connection_issue import run_locust
import boto3


def run_locust_test(event, context):
    bucket = event.get('bucket')
    test_file = event.get('file')
    s3_client = boto3.client("s3")
    downloaded_payload_file_name = f"/tmp/{test_file}"
    s3_client.download_file(bucket, test_file, downloaded_payload_file_name)
    run_locust(test_file=downloaded_payload_file_name)
