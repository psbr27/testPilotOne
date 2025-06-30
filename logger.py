import logging

def get_logger(name="TestPilot"):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] [%(filename)s:%(lineno)d] - %(message)s')
        ch.setFormatter(formatter)
        logger.addHandler(ch)

    return logger
