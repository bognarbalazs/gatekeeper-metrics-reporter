import uvicorn

from api import app
from config import ENABLE_ACCESS_LOG, HTTP_PORT, POD_IP
from log_setup import logger


def main():
    try:
        uvicorn.run(app, host=f'{POD_IP}', port=HTTP_PORT,log_config=None,access_log=ENABLE_ACCESS_LOG)
    except Exception as e:
        logger.error(e)

if __name__ == "__main__":
  main()

