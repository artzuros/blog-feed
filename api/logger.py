import logging
import sys
import os
from logging.handlers import RotatingFileHandler

def setup_logger(name: str, log_level: str = "INFO", log_file: str = "logs/api.log") -> logging.Logger:
    """Setup logger with file and console handlers."""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level))
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    # Ensure log directory exists
    log_dir = os.path.dirname(log_file)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
    
    # File handler with rotation
    file_handler = RotatingFileHandler(
        log_file, 
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s - %(funcName)s:%(lineno)d - %(message)s')
    file_handler.setFormatter(file_format)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s - %(message)s')
    console_handler.setFormatter(console_format)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

# Create loggers with defaults (will be reconfigured later if needed)
root_logger = setup_logger("blog-feed")
api_logger = setup_logger("blog-feed.api")
db_logger = setup_logger("blog-feed.db")
scan_logger = setup_logger("blog-feed.scanner")
llm_logger = setup_logger("blog-feed.llm")

def reconfigure_logging(log_level: str, log_file: str):
    """Reconfigure logging after settings are loaded."""
    global root_logger, api_logger, db_logger, scan_logger, llm_logger
    
    # Remove existing handlers
    for logger in [root_logger, api_logger, db_logger, scan_logger, llm_logger]:
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
    
    # Recreate with new settings
    root_logger = setup_logger("blog-feed", log_level, log_file)
    api_logger = setup_logger("blog-feed.api", log_level, log_file)
    db_logger = setup_logger("blog-feed.db", log_level, log_file)
    scan_logger = setup_logger("blog-feed.scanner", log_level, log_file)
    llm_logger = setup_logger("blog-feed.llm", log_level, log_file)
    
    root_logger.info(f"Logging reconfigured - Level: {log_level}, File: {log_file}")