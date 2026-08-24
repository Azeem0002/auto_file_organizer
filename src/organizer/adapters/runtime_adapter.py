
import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from loguru import logger
from platformdirs import PlatformDirs
from ..models.models import APP_DIRS, LOG_DIR


def _get_platform_dirs()-> PlatformDirs:
    return APP_DIRS

def _is_dev_env()-> bool:
    return os.getenv("APP_ENV", "dev").strip().lower() != "prod"

def _get_local_timezone():
    tz_name = os.getenv("APP_LOCAL_TZ") or os.getenv("TZ")
    if tz_name:
        try:
            return ZoneInfo(tz_name)
        except ZoneInfoNotFoundError:
            logger.warning(f"Unknown timezone: {tz_name}. "
            "Falling back to system local timezone")

    detected = datetime.now().astimezone().tzinfo
    if detected is not None:
        return detected

    return ZoneInfo("UTC") 

def _setup_env()-> Path:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    return LOG_DIR / "organizer.log"

def _setup_logger(log_file: Path):

    logger.remove()
    if not _is_dev_env():
        logger.add(
            sink=sys.stderr,
            level="INFO",
            format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
            colorize=True,
            backtrace=True,
            catch=True,
        )
    else:
        logger.add(
            sink=sys.stderr,
            level="DEBUG",
            format="<green{time:HH:mm:ss}></green> | <level>{level: <8}</level> | {message}",
            colorize=True,
            backtrace=True,
            catch=True,
        )

    logger.add(
        sink=str(log_file),
        level="DEBUG",
        format="{time:YYYY-MM_DD HH:mm:ss} | {level: <8} | {module}.{function}:{line} | {message}",
        rotation="5 MB",
        retention="14 days",
        compression="zip",
        serialize=True,
        enqueue=True,
        backtrace=True,
        catch=True
    )



#### Public function use-case ######
def get_platform_dirs()-> PlatformDirs:
    return _get_platform_dirs()

def is_dev_env()-> bool:
    return _is_dev_env()

def get_local_timezone():
    return _get_local_timezone()

def setup_env()-> Path:
    return _setup_env()

def setup_logger(log_file: Path)-> None:
    return _setup_logger(log_file)
