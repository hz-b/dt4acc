import logging
from .event import StatusChange

logger = logging.getLogger("dt4acc")


class ReportOnExitContextManager:
    def __enter__(self):
        logger.debug("Report exit enter")
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        logger.debug("Report exit")
        if exc_type is None:
            return
        logger.error(
            f"execution of trigger failed {exc_type}({exc_val})"
        )


class TriggerEnterExitContextManager:
    def __init__(self, event: StatusChange):
        assert callable(event.trigger)
        self.event = event

    def __enter__(self):
        with ReportOnExitContextManager():
            self.event.trigger(True)

    def __exit__(self, exc_type, exc_val, exc_tb):
        with ReportOnExitContextManager():
            self.event.trigger(False)