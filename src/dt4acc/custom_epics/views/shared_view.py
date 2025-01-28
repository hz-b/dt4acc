import os

from .calculation_result_view import ResultView
from ...core.utils.logger import get_logger

logger = get_logger()
# Singleton pattern for shared view instance
_view_instance = None


def get_view_instance() -> ResultView:
    global _view_instance
    if _view_instance is None:
        prefix = os.environ.get("DT4ACC_PREFIX", "Anonym")
        _view_instance = ResultView(prefix=prefix)
    return _view_instance
