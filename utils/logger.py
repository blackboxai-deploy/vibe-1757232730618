"""
Logging configuration for French Real Estate Rental Hunter
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from datetime import datetime

from config.settings import Config

def setup_logging():
    """Setup logging configuration"""
    config = Config()
    
    # Create logs directory if it doesn't exist
    config.LOGS_DIR.mkdir(exist_ok=True)
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)8s | %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, config.LOG_LEVEL))
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        config.LOG_FILE,
        maxBytes=config.LOG_MAX_SIZE,
        backupCount=config.LOG_BACKUP_COUNT,
        encoding='utf-8'
    )
    file_handler.setLevel(getattr(logging, config.LOG_LEVEL))
    file_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(file_handler)
    
    # Error file handler (separate file for errors)
    error_file = config.LOGS_DIR / 'errors.log'
    error_handler = logging.handlers.RotatingFileHandler(
        error_file,
        maxBytes=config.LOG_MAX_SIZE,
        backupCount=config.LOG_BACKUP_COUNT,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(error_handler)
    
    # Scraping-specific logger
    scraping_file = config.LOGS_DIR / 'scraping.log'
    scraping_handler = logging.handlers.RotatingFileHandler(
        scraping_file,
        maxBytes=config.LOG_MAX_SIZE,
        backupCount=config.LOG_BACKUP_COUNT,
        encoding='utf-8'
    )
    scraping_handler.setLevel(logging.DEBUG)
    scraping_handler.setFormatter(detailed_formatter)
    
    # Add scraping handler to scrapers loggers
    scraping_logger = logging.getLogger('scrapers')
    scraping_logger.addHandler(scraping_handler)
    
    # Communication-specific logger
    comm_file = config.LOGS_DIR / 'communication.log'
    comm_handler = logging.handlers.RotatingFileHandler(
        comm_file,
        maxBytes=config.LOG_MAX_SIZE,
        backupCount=config.LOG_BACKUP_COUNT,
        encoding='utf-8'
    )
    comm_handler.setLevel(logging.DEBUG)
    comm_handler.setFormatter(detailed_formatter)
    
    # Add communication handler
    comm_logger = logging.getLogger('communication')
    comm_logger.addHandler(comm_handler)
    
    # Suppress some noisy third-party loggers
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('selenium').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    
    # Log startup message
    root_logger.info("🎯 Logging system initialized")
    root_logger.info(f"📄 Log files: {config.LOGS_DIR}")
    root_logger.info(f"🔍 Log level: {config.LOG_LEVEL}")