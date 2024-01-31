import logging
logger = logging.getLogger("dt4acc")


def iointr(label, value):
    logger.info(f"{label=}:{value=}")