
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable
from pathlib import Path
from enum import StrEnum
from datetime import datetime

from platformdirs import PlatformDirs


class ValidationError(Exception):
    "Validation failure"

@dataclass
class Validated[T]:
    value: T | None = None
    errors: list[ValidationError] = field(default_factory= list)

    @property
    def is_valid(self)-> bool:
        return self.value is not None and not self.errors

    @property
    def is_invalid(self)-> bool:
        return not self.is_valid

    def get_or_raise(self)-> T:
        if self.is_invalid:
            err_msg = str(self.errors[0]) if self.errors else "invalid value"
            raise ValidationError(err_msg)

        assert self.value is not None, "Invariant broken: value must exist when valid"
        return self.value

    def map[U](self, op: Callable[[T], U])-> Validated[U]:
        if self.is_invalid:
            return Validated(None, self.errors.copy())

        assert self.value is not None, "Invariant broken: value must exist when valid"
        return Validated(op(self.value), self.errors.copy())

    def bind[U](self, op: Callable[[T], Validated[U]])-> Validated[U]:
        if self.is_invalid:
            return Validated(None, self.errors.copy())

        assert self.value is not None, "Invariant broken: value must exist when valid"
        result = op(self.value)
        return Validated(result.value, self.errors + result.errors.copy())

    def __and__[U](self, other: Validated[U])-> Validated[tuple[T, U]]:
        if self.is_valid and other.is_valid:
            assert self.value is not None
            assert other.value is not None
            return Validated((self.value, other.value), self.errors + other.errors.copy())

        return Validated(None, self.errors + other.errors.copy())


@dataclass(frozen=True)
class AppConfig:
    app_name: str = "organizer"
    app_author: str = "Al-Azeem"
    max_files: int = 10000
    backup_retry_attempts: int = 2    

APP_CONFIG = AppConfig()
MAX_FILES = APP_CONFIG.max_files
APP_DIRS = PlatformDirs(APP_CONFIG.app_name, APP_CONFIG.app_author)
BACKUP_DIR = Path(APP_DIRS.user_data_dir) / "backups"
LOG_DIR = Path(APP_DIRS.user_log_dir)
STATE_DIR = Path(APP_DIRS.user_state_dir)  # Persist crash recovery state
ORGANIZE_STATE_PATH = STATE_DIR / "organize_state.json"


class ConflictStrategy(StrEnum):
    SKIP = "skip"
    RENAME = "rename"
    OVERWRITE = "overwrite"
    DELETE = "delete"

@dataclass
class FileInfo:
    path: Path
    name: str
    stem: str
    suffix: str
    category: str
    size: int = 0
    mode: int | None = None
    modified: datetime | None = None


@dataclass
class OrganizeOperationState:
    source_dir: str
    conflict_strategy: str
    recursive: bool
    max_files: int
    started_at: str
    completed_paths: list[str] = field(default_factory= list[str])


@dataclass(frozen=True)
class OrganizeFilesInput:
    source_dir: Path
    dry_run: bool = True
    conflict_strategy: ConflictStrategy = ConflictStrategy.SKIP
    recursive: bool = False
    max_files = MAX_FILES
    backup: bool = False
    custom_map: dict[str, str] = field(default_factory=dict)


@dataclass
class OrganizationResult:
    organized: int = 0
    conflicts: int = 0
    skipped: int = 0
    overwritten: int = 0
    deleted: int = 0
    errors: int = 0
    created_categories_count: int = 0
    operations: list[tuple[Path, Path]] = field(default_factory= list) 
    discovered_categories: set[str] = field(default_factory= set)


@dataclass(frozen=True)
class DirectoryAnalysis:
    source_dir: Path
    file_count: int
    category_counts: dict[str, int]

    @property
    def categories(self)-> list[str]:
        return sorted(self.category_counts)

dataclass(frozen=True)
class DiskSpacePolicy:
    backup_buffer_percent: int
    minimum_free_percent: int
    low_space_warning_percent: int
    maximum_exact_count: int
    maximum_backup_files: int
    fast_estimate_sample_size: int
    

@dataclass(frozen=True)
class BackupCommandInput:
    source_dir: Path
    backup_dir: Path = BACKUP_DIR
    compress: bool = True
    compression_format: str = "zip"
