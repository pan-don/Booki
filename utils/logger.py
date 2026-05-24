"""
Centralized logging configuration for the RAG system.
Provides a setup function to get a logger with consistent formatting.
"""

import logging
import sys
from pathlib import Path
from typing import Optional


# Default log format (includes timestamp, level, module, and message)
DEFAULT_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Global flag to ensure we only configure once
_initialized = False


def setup_logger(
    name: str,
    log_file: Optional[Path] = None,
    level: int = logging.INFO,
    console: bool = True,
    propagate: bool = False
) -> logging.Logger:
    """
    Set up a logger with optional file handler and console handler.
    
    Args:
        name: Logger name (usually __name__).
        log_file: Path to log file (if None, no file logging).
        level: Logging level (e.g., logging.DEBUG, logging.INFO).
        console: If True, log to stdout.
        propagate: If False, prevent propagation to root logger.
        
    Returns:
        Configured logger instance.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = propagate
    
    # Remove existing handlers to avoid duplicates
    if logger.hasHandlers():
        logger.handlers.clear()
    
    formatter = logging.Formatter(DEFAULT_LOG_FORMAT, datefmt=DEFAULT_DATE_FORMAT)
    
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    if log_file:
        # Ensure directory exists
        log_file = Path(log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger without automatic configuration.
    Assumes root configuration already done (e.g., by configure_root_logger).
    """
    return logging.getLogger(name)


def configure_root_logger(
    log_file: Optional[Path] = None,
    level: int = logging.INFO,
    console: bool = True
) -> None:
    """
    Configure the root logger for the entire application.
    Call this once at application startup.
    """
    global _initialized
    if _initialized:
        return
    
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove default handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    formatter = logging.Formatter(DEFAULT_LOG_FORMAT, datefmt=DEFAULT_DATE_FORMAT)
    
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    
    if log_file:
        log_file = Path(log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    _initialized = True
    root_logger.info("Root logger configured")


# Example: create a module-level logger for utils
logger = get_logger(__name__)