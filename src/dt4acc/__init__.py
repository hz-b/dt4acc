from .config.db_config import mongodb_url as _mongodb_

mongodb_ = _mongodb_(__name__)

__all__ = ["mongodb_"]
