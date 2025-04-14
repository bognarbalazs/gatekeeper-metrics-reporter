import os

POD_IP = os.getenv("POD_IP")
HTTP_PORT = int(os.getenv("HTTP_PORT",8000))
TOKEN = os.getenv("TOKEN")
CONSTRAINTS_API_VERSION = os.getenv("CONSTRAINTS_API_VERSION",'v1beta1')
LOG_LEVEL_NAME = os.getenv("LOG_LEVEL").upper()
ENABLE_ACCESS_LOG = bool(os.getenv("ENABLE_ACCESS_LOG",True))
LOG_TO_FILE = bool(os.getenv("LOG_TO_FILE", True))
LOG_FILE_PATH = os.getenv("LOG_FILE_PATH", None)
CONSTRAINT_API_URL = "https://192.168.64.9:6443/apis/constraints.gatekeeper.sh"