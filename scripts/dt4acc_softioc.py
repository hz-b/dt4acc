import logging
logging.basicConfig(level=logging.WARNING)
from dt4acc.custom_epics.ioc.server import main


if __name__ == "__main__":
    main()