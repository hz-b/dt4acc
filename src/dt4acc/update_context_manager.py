import io
import logging
import traceback

logger = logging.getLogger("dt4cc")


class UpdateContext:
    def __init__(self, *, element_id, property_name, value, kwargs):
        self.element_id = element_id
        self.property_name = property_name
        self.value = value
        self.kwargs = kwargs

    def __enter__(self):
        # pass
        logger.debug(
            f"Updating element {self.element_id=}:"
            f"{self.property_name=} {self.value=} {self.kwargs=}"
        )

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            return
        logger.error(
            f"Could not update element {self.element_id=}:"
            f"{self.property_name=} {self.value=} {self.kwargs=}: {exc_type}({exc_val})"
        )
        marker = "-" * 78
        tb_buf = io.StringIO()
        traceback.print_tb(exc_tb, file=tb_buf)
        tb_buf.seek(0)
        logger.error("%s\nTraceback:\n%s\n%s\n", marker, tb_buf.read(), marker)
