"""
Contains facades related to managing sessions with boto3.
These facades can be used to create other boto3 facades used for accessing services.
"""

from dataclasses import dataclass
from typing import Union

from boto3.session import Session


@dataclass(frozen=True)
class AwsSession:
    """
    Helper class used to hold on to an active AWS session with boto3.
    This can be initialized from a lambda function context, which has credentials based on the lambda's IAM role,
    or it can be initialized by loading local credentials via env vars or a named profile.
    """

    session: Session
    region: str
    account_id: str
    profile: str

    @classmethod
    def create(cls, profile=None):
        """
        Create and initialize an AwsSession object.
        Args:
            profile: str - if specified, the name of a profile to use for creating the session

        Returns:
            An in stance of AwsSession
        """
        if profile:
            session = Session(profile_name=profile)
        else:
            session = Session()
        account_id = session.client("sts").get_caller_identity().get("Account")
        global _singleton
        if not _singleton:
            _singleton = cls(
                session=session, profile=session.profile_name, account_id=account_id, region=session.region_name,
            )
        return _singleton


# Module-level singleton for the session.  Generally simpler than rolling your own, and is more testable.
# AWS Sessions should be singletons and be cached, as there is a fair amount of work that goes into producing one.
_singleton: Union[AwsSession, None] = None
