
from __future__ import annotations

import errno
import shutil
import sys
import time
from functools import wraps
from datetime import datetime
from pathlib import Path

from loguru import logger
from tqdm import tqdm

from ..adapters.disk_space_adapter import DEFAULT_DISK_SPACE_POLICY, monitor_copy_progress
from ..models.models import ValidationError
from ..validators.validation import parse_backup_destination, parse_backup_source


_TRANSIENT_COPY_ERRNOS = frozenset({
    errno.EAGAIN,      
    errno.EBUSY,       
    errno.ESTALE,      
    errno.ETIMEDOUT,   
})

def _validate_paths(src_dir: Path, dst_dir: Path)-> None:

    source_validation = parse_backup_source(src_dir)
    if source_validation.is_invalid:
        err_msg = "\n".join(str(error) for error in source_validation.errors)
        raise ValidationError(f"Invalid source directory: \n{err_msg}")

    destination_validation = parse_backup_destination(dst_dir)
    if destination_validation.is_invalid:
        err_msg = "\n".join(str(error) for error in destination_validation.errors)
        raise ValidationError(f"Invalid destination directory: \n{err_msg}")

def _is_transient_copy_error(error: OSError)-> bool:
    return error.errno in _TRANSIENT_COPY_ERRNOS

def copy_single_file_secure(src_file: Path, src_root: Path, dest_root: Path)-> int:
    try:
        relative_path = src_file.relative_to(src_root)
    except ValueError as e:
        raise ValidationError(f"Security violation: file {src_file} is not under {src_root}") from e

    dest_file = dest_root / relative_path
    dest_file.parent.mkdir(parents=True, exist_ok=True)

    try:
        file_size = src_file.stat().st_size
    except OSError as e:
        raise PermissionError(f"Cannot read source file {src_file.name}") from e

    last_error: Exception | None = None
    for attempt in range(3):
        try:
            shutil.copy2(src_file, dest_file)
            if not dest_file.exists():
                raise OSError("Target file not created after copy operation")
            copied_size = dest_file.stat().st_size

            if copied_size != file_size:
                dest_file.unlink(missing_ok=True)
                raise OSError(f"Copy incomplete: {copied_size:,} of {file_size:,} bytes transferred")
            return file_size
        except OSError as error:
            last_error = error
            dest_file.unlink(missing_ok=True)
            if not _is_transient_copy_error(error):
                raise

            if attempt < 2:
                sleep_time = 0.1 * ((attempt + 1) ** 2)
                logger.debug(f"Retry {attempt + 1}/3 doe {src_file.name}: {error}, waiting {sleep_time:1f}s")
                time.sleep(sleep_time)
    raise last_error or OSError(f"Unknown error copying {src_file.name}")


def bounded_file_count(directory: Path, limit: int= 1000)-> int:

    count = 0
    for item in directory.rglob("*"):
        if item.is_file():
            count += 1
            if count >= limit:
                break
    return count

def check_copy_safety(total_items:int, started_at: float)-> None:
    safety_limit = DEFAULT_DISK_SPACE_POLICY.maximum_backup_files
    if total_items <= safety_limit:
        return

    elapsed = time.monotonic() - started_at
    raise ValidationError(f"Safety limit exceeded: {total_items:,} > {safety_limit:,} items." 
                          f"\nProcessed for {elapsed:.1fs}s before hitting limit")

def _copy_one_file(item: Path, src_dir: Path, dest_dir: Path, stats: dict[str, int])-> None:

    try:
        bytes_copied = copy_single_file_secure(item, src_dir, dest_dir)
        stats["copied"] += 1
        stats["bytes"] += bytes_copied
    except ValidationError:
        raise
    except (OSError, RuntimeError) as e:
        logger.warning(f"Failed to copy {item.name}: {e}")
        stats["skipped"] += 1
    finally:
        stats["processed"] += 1


def _copy_rates(stats: dict[str, int], elapsed: float)-> tuple[float, float]:
    if elapsed <= 0:
        return 0.0, 0.0
    return stats["copied"] / elapsed, stats["bytes"] / elapsed


def _report_copy_results(started_at: float, stats: dict[str, int], src_dir: Path, dest_dir: Path)-> None:

    elapsed = time.monotonic() - started_at
    gib = stats["bytes"] / (1024 * 1024 * 1024)
    rate, byte_rate = _copy_rates(stats, elapsed)

    logger.success(f"\nCOPY COMPLETE\nFiles copied: {stats['copied']:,}\nFiles failed: {stats['skipped']:,}\nTotal data: {gib:.2f} GiB\nCopy time: {elapsed:.1f}s\nSpeed: {rate:.1f} files/sec, {byte_rate/1024/1024:.1f} MiB/sec")
    logger.debug(f"SECURITY AUDIT LOG\nSource: {src_dir}\nDestination: {dest_dir}\nItems scanned: {stats['total_items']:,}\nFiles copied: {stats['copied']:,}\nFiles failed: {stats['skipped']:,}")

def copy_directory_with_progress_secure(src_dir: Path, dest_dir: Path)-> int:
    _validate_paths(src_dir, dest_dir)

    is_terminal = sys.stderr.isatty()
    progress_count_limit = 1000
    bounded_count = bounded_file_count(src_dir, progress_count_limit) if is_terminal else 0
    if bounded_count == 0 and is_terminal:
        logger.info("No files found")
        return 0

    if is_terminal:
        if bounded_count < progress_count_limit:
            logger.info(f"Found {bounded_count:,} files")
        else:
            logger.info(f"Found at least {bounded_count:,} files")

    start_time = time.monotonic()
    stats = {"total_items": 0, "processed": 0, "copied": 0, "skipped": 0, "bytes": 0}
    try:
        iterator = src_dir.rglob("*")
        progress_total = bounded_count if bounded_count < progress_count_limit else None
        progress = tqdm(total=progress_total, desc="Copying", unit="files") if is_terminal and bounded_count > 0 else None
        try:
            for item in iterator:
                if not item.is_file():
                    continue
                check_copy_safety(stats["total_items"] + 1, start_time)
                stats["total_items"] += 1
                _copy_one_file(item, src_dir, dest_dir, stats)
                if progress:
                    progress.update(1)
        finally:
            if progress:
                progress.close()
    except KeyboardInterrupt:
        logger.warning(f"Copy interrupted after {time.monotonic() - start_time:1f}s")
        raise
    except Exception as e:
        logger.error(f"Copy failed after {time.monotonic() - start_time:.1f}s: {e}")
        raise

    if stats["processed"] == 0:
        logger.info(f"No files found in {src_dir}")
        return 0 
    _report_copy_results(start_time, stats, src_dir, dest_dir)
    return stats["copied"]

def copy_backup_with_space_monitoring(src_dir: Path, dest_dir: Path)-> int:

    _validate_paths(src_dir, dest_dir)

    copied_files = 0
    copied_bytes = 0
    start_time = time.monotonic()
    can_monitor_space = True
    try:
        shutil.disk_usage(dest_dir)
    except OSError as e:
        can_monitor_space = False
        logger.debug(f"Cannot monitor disk space during copy: {e}." 
                     "proceeding without space checks")

    seen_files = 0
    for file_path in src_dir.rglob("*"):
        if not file_path.is_file():
            continue

        check_copy_safety(seen_files + 1, start_time)
        seen_files += 1
        try:
            file_size = file_path.stat().st_size 
        except OSError as e:
            logger.warning(f"Cannot get size for {file_path.name}: {e}")
            continue

        if can_monitor_space:
            can_copy, space_msg = monitor_copy_progress(dest_dir, file_path)
            if not can_copy:
                raise ValueError(f"Disk space exhausted after copying {copied_bytes}")
            if space_msg:
                logger.warning(space_msg)

        try:
            copied_bytes += copy_single_file_secure(file_path, src_dir, dest_dir)
            copied_bytes += 1
        except ValidationError:
            raise
        except (OSError, RuntimeError) as e:
            logger.warning(f"Failed to copy {file_path.name}: {e}")
    
    if seen_files == 0:
        logger.info(f"No files to copy from {src_dir}")
    return copied_files

def with_logging(func):

    @wraps(func)
    def wrapper(*args, **kwargs):
        logger.debug(f"Starting {func.__name__}")
        try:
            result = func(*args, **kwargs)
            logger.debug(f"Completed {func.__name__}")
            return result
        except Exception:
            logger.exception(f"{func.__name__} failed.")
            raise

    return wrapper
