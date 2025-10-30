import getpass
import os

from ..utils.logger import get_logger

logger = get_logger()

_view_instance = None


def get_view_instance():
    """
    Returns a singleton instance of the appropriate ResultView class,
    depending on the environment variable 'server'. Supports 'epics' or 'tango'.
    """
    global _view_instance
    if _view_instance is not None:
        return _view_instance

    prefix = os.environ.get("DT4ACC_PREFIX", getpass.getuser())
    server_type = os.environ.get("server", "epics").lower()

    if server_type == "tango":
        from ...custom_tango.views.result_view import ResultView
    elif server_type == "epics":
        from ...custom_epics.views.result_view import ResultView
    else:
        raise ValueError(f"Unsupported server type: {server_type}")

    _view_instance = ResultView(prefix=prefix)
    return _view_instance
