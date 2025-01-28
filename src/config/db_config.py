from configparser import ConfigParser
from importlib.resources import files
from urllib.parse import quote_plus
import os

from src.core.utils.logger import get_logger

logger = get_logger()


def config(mod_name):
    parser = ConfigParser()
    config_path = files(mod_name).joinpath("config/config.cfg")
    read_files = parser.read(config_path)

    if not read_files:
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    return parser

def mongodb_url_from_config(mod_name):
    cfg = config(mod_name)
    mongodb = cfg["default"]["mongodb"]
    dbsec = cfg[mongodb]
    server = dbsec['server']
    port = dbsec['port']
    try:
        username = dbsec['username']
    except KeyError:
        username = None   # Add username from config
    try:
        password = dbsec['password']
    except KeyError:
        password = None
    db_name = dbsec['database_name']
    if(username):
        # Encode username and password for inclusion in URL
        encoded_username = quote_plus(username)
        encoded_password = quote_plus(password)
        return f"mongodb://{encoded_username}:{encoded_password}@{server}:{port}/{db_name}"
    else: return f"mongodb://{server}:{port}/{db_name}"

def mongodb_url(mod_name):
    default_url = mongodb_url_from_config(mod_name)
    try:
        return os.environ["MONGODB_URL"]
    except KeyError:
        txt = f'Environment variable MONGODB_URL is not defined, using default: {default_url}'
        print(txt)
        logger.warning(txt)
        return default_url
