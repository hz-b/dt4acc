import logging
import pydev

logger = logging.getLogger("thor-scsi-lib")

class CalculationRunningManager:
    """
    Context manager to signal if some calculation is running on an EPICS record.

    Args:
        prefix (str): Prefix of the label. "-dt-calcs" is added to the end.

    Usage:
        with CalculationRunningManager(prefix="my-prefix"):
            # Some calculation code

    """
    def __init__(self, prefix):
        self.label = f"{prefix}-dt-calcs"
        self.running = False

    def signal(self):
        """Push running status to EPICS"""
        logger.warning(f"{self.__class__.__name__}: pydev.iointr({self.label}, {self.running})")
        pydev.iointr(self.label, self.running)

    def __enter__(self):
        self.running = True
        self.signal()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.running = False
        self.signal()
