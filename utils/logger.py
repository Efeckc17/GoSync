import logging
import sys
from pathlib import Path
import codecs

def setup_logger():
    """Setup application logging"""
    # Create logs directory
    log_dir = Path.home() / '.gosync' / 'logs'
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / 'gosync.log'
    
    # Configure logging with UTF-8 encoding
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(codecs.getwriter('utf-8')(sys.stdout.buffer))
        ]
    )
    
    # Create logger
    logger = logging.getLogger('GOSync')
    logger.setLevel(logging.INFO)
    
    return logger 