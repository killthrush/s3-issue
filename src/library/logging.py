"""
Module for logging idioms.
Based heavily on the structlog library.
"""

import inspect
import logging
import os

import structlog
from structlog._frames import _find_first_app_frame_and_name


def initialize_logging():
    log_level = os.environ.get("NGT_LOG_LEVEL") or "DEBUG"
    for_development = os.environ.get("AWS_EXECUTION_ENV") is None
    structlog.reset_defaults()
    root_logger = logging.getLogger("")
    for h in root_logger.handlers:
        root_logger.removeHandler(h)

    if for_development:
        formatter = _configure_local_dev_formatter()
    else:
        formatter = _configure_aws_lambda_formatter()

    default_handler = logging.StreamHandler()
    default_handler.setFormatter(formatter)
    root_logger.addHandler(default_handler)
    root_logger.setLevel(log_level)
    root_logger.propagate = True

    # We support logging third party libraries as well; alter these log levels if needed.
    for logger_name in ["boto3", "botocore", "asyncio"]:
        third_party_logger = logging.getLogger(logger_name)
        for h in third_party_logger.handlers:
            third_party_logger.removeHandler(h)
        third_party_logger.addHandler(default_handler)
        third_party_logger.setLevel("WARNING")


def get_logger(logger_name=None, log_context=None):
    """
    Creates and returns a structlog logger that has been bound to context data.

    Args:
        logger_name: The name of the logger that will be bound (uses standard log name conventions)
        log_context: dict - contextual information that will automatically be included in all log records.

    Returns:
        A structlog bound logger instance
    """
    if logger_name:
        logger = structlog.get_logger(logger_name)
    else:
        logger = structlog.get_logger()
    if log_context:
        logger = logger.bind(**log_context)
    return logger


def _get_shared_structlog_processors():
    """
    Define common structlog processors to make sure we get all the info we need into logs,
    including data to enrich third-party logs.

    Returns:
        list(processor) - A list of structlog processor functions
    """
    shared_processors = [
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        _show_module_info_processor,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    return shared_processors


def _configure_aws_lambda_formatter():
    """
    Create a logging formatter that can be used for all logs in an AWS Lambda environment.
    Uses structlog and formats all output to JSON.

    Returns:
        A formatter function that can be attached to standard log handlers.
    """
    lambda_processors = _get_shared_structlog_processors()
    structlog.configure(
        processors=lambda_processors + [structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        context_class=dict,
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=lambda_processors, processor=structlog.processors.JSONRenderer(),
    )
    return formatter


def _configure_local_dev_formatter():
    """
    Create a logging formatter that can be used for all logs in a local dev environment.
    Uses structlog and colorama to add some nice color-coded formatting.

    Returns:
        A formatter function that can be attached to standard log handlers.
    """
    shared_processors = _get_shared_structlog_processors()
    dev_processors = shared_processors + [structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M.%S")]
    structlog.configure(
        processors=dev_processors + [structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        context_class=dict,
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=dev_processors, processor=structlog.dev.ConsoleRenderer(),
    )
    return formatter


def _show_module_info_processor(logger, method_name, event_dict):
    """
    Get the module, function and line number corresponding to the log message.
    Derived from https://stackoverflow.com/questions/54872447/how-to-add-code-line-number-using-structlog

    Args:
        logger: str - the name of the loggers namespace
        method_name: str - the name of the function
        event_dict: dict - the contents fo the log record

    Returns:
        The event dict (modified to include the function and line number)
    """

    # If by any chance the record already contains a `call_site` key,
    # (very rare) move that into a 'call_site_original' key
    if "call_site" in event_dict:
        event_dict["call_site_original"] = event_dict["call_site"]
    f, name = _find_first_app_frame_and_name(additional_ignores=["logging", "src.library.logging"])
    if not f:
        return event_dict
    frameinfo = inspect.getframeinfo(f)
    if not frameinfo:
        return event_dict
    module = inspect.getmodule(f)
    if not module:
        return event_dict
    if frameinfo and module:
        event_dict["call_site"] = f"{ module.__name__}.{frameinfo.function}:{frameinfo.lineno}"
    return event_dict
