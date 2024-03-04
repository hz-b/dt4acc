import logging
import pydev

logger = logging.getLogger("dt4acc")


class StatusFlagView:
    def __init__(self, *, prefix):
        self.prefix = prefix

    def on_update(self, flag: bool):
        val = int(flag)
        pydev.iointr(self.prefix, val)
        logger.debug("sent label %s, val %s", self.prefix, val)
