import os
import logging
import datetime
from logging.handlers import RotatingFileHandler

class Logger:
    """Centralized logging utility for the application"""
    
    def __init__(self, name="productivity_detection", log_dir="logs", level=logging.INFO):
        """Initialize the logger"""
        self.name = name
        self.log_dir = log_dir
        self.level = level
        self.logger = None
        
        # Create logger
        self._setup_logger()
        
    def _setup_logger(self):
        """Set up the logger with handlers"""
        # Create logger
        self.logger = logging.getLogger(self.name)
        self.logger.setLevel(self.level)
        
        # Clear any existing handlers
        if self.logger.handlers:
            self.logger.handlers.clear()
        
        # Create console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(self.level)
        
        # Create file handler
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
            
        log_file = os.path.join(
            self.log_dir, 
            f"{self.name}_{datetime.datetime.now().strftime('%Y%m%d')}.log"
        )
        
        file_handler = RotatingFileHandler(
            log_file, 
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(self.level)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Add formatter to handlers
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)
        
        # Add handlers to logger
        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)
        
    def debug(self, message):
        """Log debug message"""
        self.logger.debug(message)
        
    def info(self, message):
        """Log info message"""
        self.logger.info(message)
        
    def warning(self, message):
        """Log warning message"""
        self.logger.warning(message)
        
    def error(self, message):
        """Log error message"""
        self.logger.error(message)
        
    def critical(self, message):
        """Log critical message"""
        self.logger.critical(message)
        
    def exception(self, message):
        """Log exception with traceback"""
        self.logger.exception(message)
        
# Create a default logger instance
default_logger = Logger()