"""
Logging functionality for the RFID Audio Player.

This module provides a centralized logging system that writes to both
console and a log file for the application.
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv

load_dotenv()

LOG_DIR = os.getenv("LOG_DIR")
LOG_FILE = os.path.join(LOG_DIR, "rfid_player.log")

os.makedirs(LOG_DIR, exist_ok=True)

logger = logging.getLogger()
logger.setLevel(logging.INFO)  # Default level

log_format = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

file_handler = RotatingFileHandler(LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=10)
file_handler.setFormatter(log_format)
logger.addHandler(file_handler)

console_handler = logging.StreamHandler()
console_handler.setFormatter(log_format)
logger.addHandler(console_handler)


def get_logger(name=None):
    """
    Get a logger instance with the given name.

    Args:
        name (str, optional): Logger name, usually the module name

    Returns:
        logging.Logger: A configured logger instance
    """
    if name:
        return logging.getLogger(name)
    return logger


def set_log_level(level):
    """
    Set the logging level for all handlers.

    Args:
        level: Logging level (e.g., logging.DEBUG, logging.INFO)
    """
    logger.setLevel(level)
    for handler in logger.handlers:
        handler.setLevel(level)
