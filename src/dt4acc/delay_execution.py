import logging
import threading
import time
import datetime
import pydev

from .pending_calculation_manager import PendingCalculationManager


logger = logging.getLogger("thor-scsi-lib")


class DelayExecution:
    """Only execute if no changes have been made recently

    Allows to gather many changes before one execution occurs
    """

    def __init__(self, *, prefix, callback, delay):
        """
        Args:
            prefix (str): Prefix to use for the label in `pydev.iointr()`.
            callback (callable): Callback function to execute after delay.
            delay (float): Delay in seconds before executing the callback.
        """
        self.callback = callback
        self.delay = float(delay)
        self.pending = False
        self.lock = threading.Lock()
        self.execution = PendingCalculationManager(info="delayed execution")
        self.label = f"{prefix}-dt-delayed-calcs"
        logger.debug("pydev.iointr(%s, %s)", self.label, self.pending)
        pydev.iointr(self.label, self.execution.pending)

    def request_execution(self):
        """Request execution

        In first prototype hack called `tic`
        """
        with self.lock:
            if self.pending:
                # Execution already pending
                logger.debug("Execution already pending")
                return

            self.pending = True
            logger.debug("pydev.iointr(%s, %s)", self.label, self.pending)
            pydev.iointr(self.label, self.pending)
            logger.info("Delayed execution requested")
            self.request_timestamp = datetime.datetime.now()

            # Start timer to check for changes
            thread = threading.Thread(target=self.check_for_changes)
            thread.start()
            logger.info("Leaving request_execution")

    def check_for_changes(self):
        """Check if changes have been made

        In first prototype hack called `tac`
        """
        time.sleep(self.delay)
        with self.lock:
            if self.pending:
                logger.info("Delayed execution: start")
                with self.execution:
                    self.callback()
                self.pending = False
                logger.debug("pydev.iointr(%s, %s)", self.label, self.pending)
                pydev.iointr(self.label, self.pending)
                logger.info("Delayed execution: end")

    def cancel_execution(self):
        """Cancel pending execution"""
        with self.lock:
            self.pending = False
            logger.debug("pydev.iointr(%s, %s)", self.label, self.pending)
            pydev.iointr(self.label, self.pending)
            logger.warning("Delayed execution cancelled")
