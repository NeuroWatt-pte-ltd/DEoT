import logging 
import os 
from dotenv import load_dotenv 

def setup_logger(name: str):
    """
    Set up a logger instance with the specified name.

    :param name: Logger name
    :return: Configured logger instance 
    """

    # Map log level strings to logging constants
    log_levels = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL
    }

    # Load environemnt variable, including the log level 
    load_dotenv()
    log_level = log_levels.get(os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO)

    # Create a logger and set its logging level 
    logger = logging.getLogger(name)
    logger.setLevel(log_level)

    # If the logger alreadu has handlers, return it directly
    if logger.handlers:
        return logger 

    # Create a stream handler, set its format and logging level 
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("%(asctime)s - %(levelname)s - [%(name)s] - %(message)s")
    )

    handler.setLevel(log_level)

    # Add the handler to the logger 
    logger.addHandler(handler)

    # Prevent log propagation
    logger.propagate = False 

    return logger 

    