import logging
import os
from datetime import datetime
from typing import Optional

# Global log level that can be set by CLI arguments
_global_log_level = logging.INFO


def set_global_log_level(level):
    """Set the global log level for all loggers created by get_logger."""
    global _global_log_level
    if isinstance(level, str):
        _global_log_level = getattr(logging, level.upper())
    else:
        _global_log_level = level


def get_logger(
    name: str = "TestPilot",
    log_to_file: bool = True,
    log_dir: str = "logs",
    level: Optional[str] = None,
) -> logging.Logger:
    """
    Get a logger with both console and file output.

    Args:
        name: Logger name
        log_to_file: Whether to enable file logging
        log_dir: Directory for log files
        level: Optional specific log level for this logger (overrides global)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Use specific level if provided, otherwise use global level
    if level:
        log_level = (
            getattr(logging, level.upper())
            if isinstance(level, str)
            else level
        )
    else:
        log_level = _global_log_level

    logger.setLevel(log_level)
    logger.propagate = False  # Prevent double logging by disabling propagation

    if not logger.handlers:
        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [%(name)s] [%(filename)s:%(lineno)d] - %(message)s"
        )

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)  # Use the same level as logger
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # File handler (if enabled)
        if log_to_file:
            try:
                # Create logs directory if it doesn't exist
                os.makedirs(log_dir, exist_ok=True)

                # General log file with timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                log_file = os.path.join(log_dir, f"testpilot_{timestamp}.log")

                file_handler = logging.FileHandler(
                    log_file, mode="w", encoding="utf-8"
                )
                file_handler.setLevel(
                    logging.DEBUG
                )  # File gets more detailed logs
                file_handler.setFormatter(formatter)
                logger.addHandler(file_handler)

                # Separate error/failure log file
                error_log_file = os.path.join(
                    log_dir, f"testpilot_failures_{timestamp}.log"
                )
                error_handler = logging.FileHandler(
                    error_log_file, mode="w", encoding="utf-8"
                )
                error_handler.setLevel(
                    logging.ERROR
                )  # Only errors and failures
                error_handler.setFormatter(formatter)
                logger.addHandler(error_handler)

                logger.debug(
                    f"Logging to files: {log_file} and {error_log_file}"
                )

            except (OSError, PermissionError) as e:
                logger.warning(
                    f"Could not setup file logging: {e}. Continuing with console-only logging."
                )

    return logger


def get_failure_logger(name: str = "TestPilot.Failures") -> logging.Logger:
    """
    Get a dedicated logger for test failures with structured output.

    Returns:
        Logger configured specifically for failure reporting
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.ERROR)
    logger.propagate = False  # Prevent double logging by disabling propagation

    if not logger.handlers:
        # Create logs directory
        os.makedirs("logs", exist_ok=True)

        # Failure-specific log file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        failure_log_file = os.path.join(
            "logs", f"test_failures_{timestamp}.log"
        )

        try:
            handler = logging.FileHandler(
                failure_log_file, mode="w", encoding="utf-8"
            )
            handler.setLevel(logging.ERROR)

            # Structured formatter for failures
            formatter = logging.Formatter(
                "%(asctime)s|%(levelname)s|%(message)s"
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        except (OSError, PermissionError) as e:
            # Fallback to main logger if file creation fails
            main_logger = get_logger("TestPilot")
            main_logger.warning(f"Could not create failure log file: {e}")

    return logger
