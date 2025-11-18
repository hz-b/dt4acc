import functools
import logging
logging.basicConfig(level=logging.WARNING)

@functools.lru_cache(maxsize=None)
def setup_logger(name):
    """
    Setup and return a logger.
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.WARNING)
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger

def get_logger():
    return setup_logger("dt4acc")
    # return logging.getLogger("dt4acc")
