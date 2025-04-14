import logging
import logging.config

import logzero

from config import LOG_FILE_PATH, LOG_LEVEL_NAME, LOG_TO_FILE

LOG_LEVELS = {
    "DEBUG": logzero.DEBUG,
    "INFO": logzero.INFO,
    "WARNING": logzero.WARN,
    "ERROR": logzero.ERROR,
    "CRITICAL": logzero.CRITICAL
}


# Uvicorn konfigurálása az indításhoz
def configure_uvicorn_logging(log_level: str) -> logging.config.DictConfigurator:
    # Logzero konfiguráció az Uvicorn számára
    log_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "()": "logging.Formatter",
                "fmt": "%(levelprefix)s %(message)s",
            },
        },
        "handlers": {
            "default": {
                "formatter": "default",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stderr",
            },
        },
        "loggers": {
            "uvicorn": {"handlers": ["default"], "level": log_level, "propagate": False},
            "uvicorn.error": {"handlers": ["default"], "level": log_level, "propagate": False},
            "uvicorn.access": {"handlers": ["default"], "level": log_level, "propagate": False},
        },
    }
    return log_config

# Logzero beállítása
def setup_logging(log_level_name: str,log_to_file: bool, log_file_path: str) -> logging.Logger:
    # Log formátum beállítása
    log_format = "[%(levelname)1.1s %(logger)s %(asctime)s %(module)s:%(lineno)d] %(message)s"
    formatter = logzero.LogFormatter(fmt=log_format,color=False)

    log_level = LOG_LEVELS.get(log_level_name, logzero.INFO)
    # Alapértelmezett logzero logger beállítása

    logzero.loglevel(log_level)
    logzero.formatter(formatter)
    logzero.json()
    configure_uvicorn_logging(log_level)

    # Set up file logging if log file is specified
    if log_to_file and log_file_path:
        logzero.logfile(
            log_file_path,
            formatter=formatter,
            maxBytes=10**7,  # 10 MB
            backupCount=3,  # Keep 3 backup copies
            encoding="utf-8",
        )
    
    # Root logger beállítása
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Logzero handlerek hozzáadása a root loggerhez
    for handler in logzero.logger.handlers:
        root_logger.addHandler(handler)
    
    # Uvicorn és FastAPI loggerek beállítása
    for logger_name in ["uvicorn", "uvicorn.access", "uvicorn.error", "fastapi"]:
        module_logger = logging.getLogger(logger_name)
        module_logger.handlers = []
        for handler in logzero.logger.handlers:
            module_logger.addHandler(handler)
        module_logger.setLevel(log_level)
        module_logger.propagate = False     


    
    return logzero.logger

logger = setup_logging(log_level_name=LOG_LEVEL_NAME, log_to_file=LOG_TO_FILE, log_file_path=LOG_FILE_PATH)