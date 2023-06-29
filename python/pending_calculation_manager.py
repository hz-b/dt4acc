import traceback
import logging

# Set up the logger
logger = logging.getLogger("thor-scsi-lib")

class PendingCalculationManager:
    """Manages pending calculations and executes them if necessary.

    To request a calculation, set the `pending` attribute to `True`.

    Todo:
        Determine whether setting `pending` should be an attribute method.

    Args:
        info (str): Information about the calculation being managed.

    Attributes:
        pending (bool): Indicates whether a calculation is pending.
        info (str): Information about the calculation being managed.

    """

    def __init__(self, info: str):
        """Initializes a new instance of the PendingCalculationManager class.

        Args:
            info (str): Information about the calculation being managed.

        """
        self.pending = False
        self.info = info

    def __enter__(self):
        """Enters the context managed by this object.

        Returns:
            None

        """
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exits the context managed by this object.

        If no exception was raised, sets the `pending` attribute to `False`. Otherwise, logs an error message
        containing information about the calculation that failed.

        Args:
            exc_type (Type[BaseException]): The type of the exception that was raised.
            exc_val (BaseException): The exception that was raised.
            exc_tb (types.TracebackType): The traceback associated with the exception.

        Returns:
            bool: A value indicating whether the exception was handled.

        """
        if exc_type is None:
            self.pending = False
        else:
            logger.error(f"Failed to calculate {self.info}: {exc_type} {exc_val}")
            traceback.print_tb(exc_tb)
            logger.error(exc_tb)
        return True
