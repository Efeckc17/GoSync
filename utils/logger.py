import logging
import sys
from pathlib import Path
import codecs

def setup_logger():
    
    
    log_dir = Path.home() / '.gosync' / 'logs'
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / 'gosync.log'
    
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(codecs.getwriter('utf-8')(sys.stdout.buffer))
        ]
    )
    
    
    logger = logging.getLogger('GOSync')
    logger.setLevel(logging.INFO)
    
    return logger 