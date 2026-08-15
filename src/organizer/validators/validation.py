import os
import time
from pathlib import Path
from functools import partial

from models import Validated, ValidationError, ConflictStrategy

def validate_path_exists(path: Path)-> Validated[Path]:

    if not path.exists():
        return Validated(None, [ValidationError(f"Path does not exist: {path}")])
    return Validated(path)

def validate_is_dir(path: Path)-> Validated[Path]:
    if not path.is_dir():
        return Validated(None, [ValidationError(f"Path is not a directory: {path}")])
    return Validated(path)

def validate_is_readable(path: Path)-> Validated[Path]:
    try:
        next(path.iterdir(), None)
        return Validated(path)
    except PermissionError:
        return Validated(None, [ValidationError(f"No permission for directory")])

def validate_file_count(dir: Path, max_files)-> Validated[Path]:
    try:
        count = 0
        for i in dir.iterdir():
            if i.is_file():
                count += 1
                if count > max_files:
                    return Validated(None, [ValidationError(f"Cannot Exceed {max_files} files")])
        return Validated(dir)
    except OSError as e:
        return Validated(None, [ValidationError(f"Cannot access directory: {e}")])


def validate_within_base(path: Path, base_dir: Path)-> Validated[Path]:
    try:
        resolved = path.resolve()
        if not resolved.is_relative_to(base_dir):
            return Validated(None, [ValidationError(f"Path is outside the allowed area: {path}")])
        return Validated(resolved)
    except (OSError, RuntimeError) as e:
        return Validated(None, [ValidationError(f"Invalid path: {e}")])

def validate_not_symlink(path: Path)-> Validated[Path]:

    current = path
    while current != current.parent:
        if current.is_symlink():
            return Validated(None, [ValidationError(f"Symlink found in path: {current}")])
        current = current.parent
    return Validated(path)

def validate_is_writable_secure(path: Path)-> Validated[Path]:

    if path.exists():
        if not path.is_dir():
            return Validated(None, [ValidationError(f"Path is not a directory")])

        test_name = f".write_test_{os.getpid()}_{int(time.time())}_{os.urandom(4).hex()}"
        test_file = path / test_name

        try:
            test_file.touch(exist_ok=True)
            test_file.unlink(missing_ok=True)
            return Validated(path)
        except FileExistsError:
            return Validated(None, [ValidationError(f"Test file collision. retry: {path}")])
        except PermissionError:
            return Validated(None, [ValidationError(f"test file has no writable permission: {path}")])

    parent = path.parent
    if not parent.exists():
        return Validated(None,[ValidationError(f"parent doesn't exist: {path}")])
    return validate_is_writable_secure(parent)

def parse_source_dir_secure(path: Path, max_files: int = 10000)-> Validated[Path]:

    check_file_limit = partial(validate_file_count, max_files = max_files)
    return (
        validate_within_base(path, path.home())
        .bind(validate_path_exists)
        .bind(validate_is_dir)
        .bind(validate_is_readable)
        .bind(check_file_limit)
    )

def parse_backup_source(path: Path)-> Validated[Path]:
    return (
        validate_path_exists(path)
        .bind(validate_is_dir)
        .bind(validate_is_readable)
    )

def parse_backup_destination(path: Path)-> Validated[Path]:

    def parse_directory_or_creatable(candidate: Path)-> Validated[Path]:

        if candidate.exists():
            return validate_is_dir(candidate)

        parent_validation = validate_path_exists(candidate.parent).bind(validate_is_writable_secure)
        if parent_validation.is_valid:
            return Validated(candidate)
        return Validated(None, [ValidationError(f"")])

    return (
        validate_within_base(path, path.home())
        .bind(parse_directory_or_creatable)
        .bind(validate_not_symlink)
        .bind(validate_is_writable_secure)
    )


def parse_conflict_strategy(value: str)-> Validated[ConflictStrategy]:

    valid_options = ", ".join(strategy.value for strategy in ConflictStrategy)

    try:
        clean_value = value.strip().lower()
        if clean_value.isalnum():
            return Validated(None, [ValidationError(f"Invalid character in strategy")])

        return Validated(ConflictStrategy(clean_value))
    except ValueError:
        return Validated(None, [ValidationError(f"Invalid value. Choose from {valid_options}")])
    except (TypeError, AttributeError):
        return Validated(None, [ValidationError(f"Invalid input. Choose from {valid_options}")])
    