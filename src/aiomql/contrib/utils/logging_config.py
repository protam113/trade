import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for console output"""
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
    }
    RESET = '\033[0m'
    
    # Emoji prefixes for different log types
    EMOJI = {
        'DEBUG': '🔍',
        'INFO': 'ℹ️ ',
        'WARNING': '⚠️ ',
        'ERROR': '❌',
        'CRITICAL': '🚨',
    }
    
    def format(self, record):
        # Add color and emoji
        log_color = self.COLORS.get(record.levelname, self.RESET)
        emoji = self.EMOJI.get(record.levelname, '')
        
        # Format the message
        message = super().format(record)
        
        # Apply color to the entire message
        colored_message = f"{log_color}{emoji} {message}{self.RESET}"
        
        return colored_message


def setup_logging(config: dict):
    """
    Setup comprehensive logging configuration
    
    Args:
        config: Dictionary with logging configuration
            {
                "level": "INFO",  # DEBUG, INFO, WARNING, ERROR, CRITICAL
                "file": "bot_logs.log",
                "max_bytes": 10485760,  # 10MB
                "backup_count": 5,
                "console_level": "INFO"  # Optional, defaults to same as level
            }
    """
    log_config = config.get("logging", {})
    
    # Get configuration
    log_level = getattr(logging, log_config.get("level", "INFO").upper())
    log_file = log_config.get("file", "bot_logs.log")
    max_bytes = log_config.get("max_bytes", 10485760)  # 10MB
    backup_count = log_config.get("backup_count", 5)
    console_level = getattr(logging, log_config.get("console_level", log_config.get("level", "INFO")).upper())
    
    # Create logs directory if it doesn't exist
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # Capture everything, filter at handler level
    
    # Clear any existing handlers
    root_logger.handlers.clear()
    
    # ==================== FILE HANDLER ====================
    # Detailed logs to file
    file_formatter = logging.Formatter(
        fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)
    
    # ==================== CONSOLE HANDLER ====================
    # Colored, simplified logs to console
    console_formatter = ColoredFormatter(
        fmt='%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%H:%M:%S'
    )
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(console_level)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # ==================== SEPARATE SIGNAL LOG ====================
    # Create a separate file for trade signals only
    signal_log_file = log_path.parent / f"signals_{log_path.stem}.log"
    signal_formatter = logging.Formatter(
        fmt='%(asctime)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    signal_handler = RotatingFileHandler(
        signal_log_file,
        maxBytes=max_bytes // 2,  # Smaller file
        backupCount=backup_count,
        encoding='utf-8'
    )
    signal_handler.setLevel(logging.INFO)
    signal_handler.setFormatter(signal_formatter)
    
    # Create signal logger
    signal_logger = logging.getLogger('signals')
    signal_logger.setLevel(logging.INFO)
    signal_logger.addHandler(signal_handler)
    signal_logger.propagate = False  # Don't propagate to root logger
    
    # ==================== SUPPRESS NOISY LIBRARIES ====================
    # Reduce noise from common libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('asyncio').setLevel(logging.WARNING)
    
    # Log initialization
    root_logger.info("="*60)
    root_logger.info("📝 Logging system initialized")
    root_logger.info(f"   File log level: {logging.getLevelName(log_level)}")
    root_logger.info(f"   Console log level: {logging.getLevelName(console_level)}")
    root_logger.info(f"   Log file: {log_file}")
    root_logger.info(f"   Signal file: {signal_log_file}")
    root_logger.info(f"   Max file size: {max_bytes / 1024 / 1024:.1f} MB")
    root_logger.info(f"   Backup count: {backup_count}")
    root_logger.info("="*60)
    
    return root_logger


def log_signal(symbol: str, signal_type: str, details: dict):
    """
    Log trading signals to separate signal file
    
    Args:
        symbol: Trading symbol
        signal_type: "BUY", "SELL", "CLOSE", etc.
        details: Dictionary with signal details
    """
    signal_logger = logging.getLogger('signals')
    
    message = f"{signal_type:5s} | {symbol:10s} | "
    message += " | ".join([f"{k}={v}" for k, v in details.items()])
    
    signal_logger.info(message)


def log_trade_execution(symbol: str, success: bool, details: dict):
    """
    Log trade execution results
    
    Args:
        symbol: Trading symbol
        success: True if trade succeeded
        details: Dictionary with execution details
    """
    signal_logger = logging.getLogger('signals')
    
    status = "SUCCESS" if success else "FAILED"
    message = f"EXEC  | {symbol:10s} | {status:7s} | "
    message += " | ".join([f"{k}={v}" for k, v in details.items()])
    
    signal_logger.info(message)


# Example usage in strategy
def example_usage():
    """Example of how to use the logging system in your strategy"""
    
    # In your main file or strategy __init__
    import json
    
    with open('config.json', 'r') as f:
        config = json.load(f)
    
    # Setup logging
    logger = setup_logging(config)
    
    # Normal logging in strategy
    logger.info("Starting strategy...")
    logger.debug("Debug information")
    logger.warning("Warning message")
    logger.error("Error occurred")
    
    # Log signals
    log_signal(
        symbol="EURUSD",
        signal_type="BUY",
        details={
            "price": 1.08450,
            "tp": 1.08650,
            "sl": 1.08300,
            "ltf_trend": "bullish",
            "htf_trend": "bullish"
        }
    )
    
    # Log execution
    log_trade_execution(
        symbol="EURUSD",
        success=True,
        details={
            "ticket": 123456,
            "entry": 1.08450,
            "volume": 0.02
        }
    )