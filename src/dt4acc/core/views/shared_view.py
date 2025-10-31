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
        # For Tango, prefix must be in format: server_name/instance_name
        # Check for TANGO_SERVER_NAME and TANGO_INSTANCE_NAME env vars first
        # waheed ! only one changes need be adjusted wiht epics and env variables 
        # i have set the server name and instance name in the tango_server.py file please check it if not feasible you can change it and let me know
        server_name = os.environ.get("TANGO_SERVER_NAME", "SimpleTangoServer")
        instance_name = os.environ.get("TANGO_INSTANCE_NAME", "test")
        prefix = f"{server_name}/{instance_name}"
    elif server_type == "epics":
        from ...custom_epics.views.result_view import ResultView
        # For EPICS, use DT4ACC_PREFIX or username
        prefix = os.environ.get("DT4ACC_PREFIX", getpass.getuser())
    else:
        raise ValueError(f"Unsupported server type: {server_type}")

    _view_instance = ResultView(prefix=prefix)
    return _view_instance
