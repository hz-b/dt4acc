import logging
import pydev

logger = logging.getLogger("dt4acc")


class CalculationProgressView:
    def __init__(self, *, prefix):
        self.prefix = prefix

    def on_update(self, flag: bool):
        val = int(flag)
        logger.warning("sending label %s, val %s", self.prefix, val)
        pydev.iointr(self.prefix, val)
