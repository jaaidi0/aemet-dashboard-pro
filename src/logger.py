# src/logger.py

import logging
from datetime import datetime

class AgroFormatter(logging.Formatter):
    COLORS = {
        "INFO": "\033[92m",       # Verde
        "WARNING": "\033[93m",    # Amarillo
        "ERROR": "\033[91m",      # Rojo
    }
    ICONS = {
        "INFO": "🌱",
        "WARNING": "⚠️",
        "ERROR": "🔥",
    }
    RESET = "\033[0m"

    def format(self, record):
        color = self.COLORS.get(record.levelname, "")
        icon = self.ICONS.get(record.levelname, "")
        ts = datetime.now().strftime("%H:%M:%S")
        msg = super().format(record)
        return f"{color}[{ts}] {icon}  {msg}{self.RESET}"


def setup_logger():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    handler = logging.StreamHandler()
    handler.setFormatter(AgroFormatter("%(message)s"))

    logger.handlers.clear()
    logger.addHandler(handler)

    # Silenciamos ruido
    for spam in ["kaleido", "choreographer", "urllib3", "PIL"]:
        logging.getLogger(spam).setLevel(logging.ERROR)

    return logger
