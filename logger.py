import logging
import sys
from pathlib import Path

LOGPATH=Path('~/pysensor/log/pysensor.log').expanduser().absolute()

logger = logging
logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(module)s %(funcName)s: %(message)s",
        datefmt="%b %d %H:%M:%S",
        handlers=[
            logging.FileHandler(LOGPATH),
            logging.StreamHandler(sys.stdout)
            ]
        )


