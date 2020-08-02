"""
Contains facades for managing presigned URLs for S3.
"""

from dataclasses import dataclass
from typing import Union, Any

from botocore.client import Config


@dataclass(frozen=True)
class S3LinkSigner:
    """
    Facade class used to sign links for secure storage and retrieval of objects in S3.
    """

    s3_client: Any
    aws_session: Any

    def generate_presigned_put(self, bucket_name, object_name, content_type, timeout_in_seconds=300):
        """
        Generate a presigned PUT URL for an S3 object
        Args:
            bucket_name: str - the name of the bucket being used
            object_name: str - the unique key of the object to PUT
            content_type: str - the content-type to associate with the object; will become object metadata
            timeout_in_seconds: int - the timeout in seconds for the link. Expired links cannot be used.

        Returns:
            str - the presigned URL
        """
        if not all({bucket_name, object_name, content_type}):
            raise ValueError("Bucket name, object name, and content type are required")
        try:
            assert int(timeout_in_seconds) > 0
        except Exception:
            raise ValueError("Timeout must be int greater than zero")
        presign_response = self.s3_client.generate_presigned_url(
            ClientMethod="put_object",
            Params={"Bucket": bucket_name, "Key": object_name, "ContentType": content_type},
            ExpiresIn=timeout_in_seconds,
        )
        return presign_response

    def generate_presigned_get(self, bucket_name, object_name, content_type=None, timeout_in_seconds=300):
        """
        Generate a presigned GET URL for an S3 object
        Args:
            bucket_name: str - the name of the bucket being used
            object_name: str - the unique key of the object to GET
            content_type: str - the (optional) content-type to apply to the object when downloading;
                           may be different than the one stored with the object.
            timeout_in_seconds: int - the timeout in seconds for the link. Expired links cannot be used.

        Returns:
            str - the presigned URL
        """
        if not all({bucket_name, object_name}):
            raise ValueError("Bucket and object names are required")
        try:
            assert int(timeout_in_seconds) > 0
        except Exception:
            raise ValueError("Timeout must be int greater than zero")
        presign_response = self.s3_client.generate_presigned_url(
            ClientMethod="get_object",
            Params={
                "Bucket": bucket_name,
                "Key": object_name,
                "ResponseContentType": content_type or "application/octet-stream",
                "ResponseContentDisposition": "attachment",
            },
            ExpiresIn=timeout_in_seconds,
        )
        return presign_response

    @classmethod
    def create(cls, aws_session):
        """
        Create and initialize an S3LinkSigner object.
        Args:
            aws_session: AwsSession - a stateful facade that holds an initialized boto3 session

        Returns:
            An instance of S3LinkSigner
        """
        if not aws_session:
            raise ValueError("An active aws_session is required")
        global _singleton
        if not _singleton:
            s3_client = aws_session.session.client(
                "s3", aws_session.region, config=Config(s3={"addressing_style": "virtual"}, signature_version="s3v4"),
            )
            _singleton = cls(aws_session=aws_session, s3_client=s3_client)
        return _singleton


# Module-level singleton for the facade.  Generally simpler than rolling your own, and is more testable.
# Boto3 (specifically botocore) generates python code dynamically, so once we have created a client (in this case
# one for S3), it's a good idea to cache it for future use.
_singleton: Union[S3LinkSigner, None] = None
