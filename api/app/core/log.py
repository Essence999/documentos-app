import sys

from loguru import logger

logger.remove()

logger.add(sys.stdout, enqueue=True, level='DEBUG', backtrace=False, diagnose=False)

logger.add(
    'logs/app.log',
    rotation='10 MB',
    retention='1 month',
    level='DEBUG',
    serialize=True,
    enqueue=True,
    backtrace=False,
    diagnose=False,
)
