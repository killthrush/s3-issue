
from src.library.logging import initialize_logging, get_logger
from src.s3_connection_issue import run_locust
import boto3

initialize_logging()


def run_locust_test(event, context):
    bucket = event.get('bucket')
    test_file = event.get('file')
    logger = get_logger(log_context={"bucket": bucket, "test_file": test_file})
    s3_client = boto3.client("s3")
    downloaded_payload_file_name = f"/tmp/{test_file}"
    logger.info(f"Downloading test file: {test_file} from {bucket}")
    s3_client.download_file(bucket, test_file, downloaded_payload_file_name)
    logger.info(f"Download successful: {test_file}")
    run_locust(test_file=test_file, directory="/tmp", profile=None)
