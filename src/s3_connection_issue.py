import shutil
from time import time
from uuid import uuid4

from locust import HttpUser, constant, task
from locust.clients import HttpSession
from locust.event import EventHook

from src.library.aws_session import AwsSession
from src.library.logging import initialize_logging, get_logger
from src.library.s3_signing import S3LinkSigner

initialize_logging()


BUCKET_NAME = "devbenpeterson-document-store-530561302918"
CONCURRENT_USERS = 5
LINK_TIMEOUT_VALUE = 10
WORKING_DIRECTORY = "/Users/ben.peterson/testfiles/40mb"
SOURCE_FILE = f"{WORKING_DIRECTORY}/00"


class DocStorageUser(HttpUser):
    wait_time = constant(1)
    host = f"https://{BUCKET_NAME}.s3.amazonaws.com"
    link_signer = None
    file_id = None
    logger = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        success = EventHook()
        success.add_listener(self.success)
        failed = EventHook()
        failed.add_listener(self.failed)

        self.client = HttpSession(base_url=self.host, request_success=success, request_failure=failed)
        self.client.keep_alive = True

        aws_session = AwsSession.create()
        self.link_signer = S3LinkSigner.create(aws_session=aws_session)

    def success(self, **kwargs):
        self.logger = self.logger.bind(**kwargs)
        self.logger.info(f"Successful S3 transfer")

    def failed(self, **kwargs):
        output = {
            "url": kwargs['exception'].request.url,
            "verb": kwargs['request_type'],
            "headers": {k: v for k, v in kwargs['exception'].request.headers.items()},
            "response_time": kwargs['response_time'],
            "error": str(kwargs['exception']),
        }
        self.logger = self.logger.bind(**output)
        self.logger.error(f"Failed to process S3 transfer")

    @task()
    def start_upload(self):
        self.file_id = uuid4()
        self.logger = get_logger(log_context={"file_id": self.file_id})
        shutil.copy(SOURCE_FILE, f"{WORKING_DIRECTORY}/{self.file_id}")

        object_name = f"testdocs/{self.file_id}"
        content_type = "application/octet-stream"
        start = time()
        link = self.link_signer.generate_presigned_put(bucket_name=BUCKET_NAME,
                                                       object_name=object_name,
                                                       content_type=content_type,
                                                       timeout_in_seconds=LINK_TIMEOUT_VALUE)
        with open(f"{WORKING_DIRECTORY}/{self.file_id}", "rb") as f:
            end = time()
            self.logger.info(f"Uploading file, link age is {end - start} seconds")
            upload_response = self.client.put(link, data=f, headers={"Content-Type": content_type}, timeout=3000)
            pass


if __name__ == "__main__":
    from locust.env import Environment
    from locust.stats import stats_printer
    import gevent
    env = Environment(user_classes=[DocStorageUser])
    env.create_local_runner()
    env.runner.start(CONCURRENT_USERS, hatch_rate=1)
    env.runner.greenlet.join()

    # start a greenlet that periodically outputs the current stats
    gevent.spawn(stats_printer(env.stats))

    # in 60 seconds stop the runner
    gevent.spawn_later(60, lambda: env.runner.quit())

    # wait for the greenlets
    env.runner.greenlet.join()