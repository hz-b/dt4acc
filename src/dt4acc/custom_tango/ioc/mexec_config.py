import os

_MANAGER_HOST = "127.0.0.1"
_MANAGER_PORT = int(os.environ.get("DT4ACC_MEXEC_PORT", "50200"))
_MANAGER_AUTHKEY = b"dt4acc-tango-secret"
