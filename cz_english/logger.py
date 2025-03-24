import logging
import os
from datetime import datetime

class Logger:
    def __init__(self, log_level=logging.INFO, log_dir="logs"):
        """Initialize the logger with specified log level and directory."""
        self.log_level = log_level
        self.log_dir = log_dir
        
        # Create logs directory if it doesn't exist
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # Set up logger
        self.logger = logging.getLogger("app_logger")
        self.logger.setLevel(log_level)
        
        # Clear any existing handlers
        if self.logger.handlers:
            self.logger.handlers.clear()
        
        # Create file handler with timestamp in filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(log_dir, f"app_{timestamp}.log")
        file_handler = logging.FileHandler(log_file)
        
        # Create console handler
        console_handler = logging.StreamHandler()
        
        # Create formatter and add it to the handlers
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # Add handlers to logger
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def info(self, message):
        """Log an info message."""
        self.logger.info(message)
    
    def warning(self, message):
        """Log a warning message."""
        self.logger.warning(message)
    
    def error(self, message):
        """Log an error message."""
        self.logger.error(message)
    
    def debug(self, message):
        """Log a debug message."""
        self.logger.debug(message)
    
    def critical(self, message):
        """Log a critical message."""
        self.logger.critical(message)

# Create a default logger instance
app_logger = Logger()
