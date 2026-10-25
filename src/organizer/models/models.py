from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path


class ValidationError(Exception):
    """Raised when an organizer input fails validation."""


@dataclass(frozen=True)
class AppConfig:
    app_name: str = "file-organizer"
    app_author: str = "File Organizer"
    max_files: int = 300


APP_CONFIG = AppConfig()
MAX_FILES = APP_CONFIG.max_files
class ConflictStrategy(StrEnum):
    SKIP = "skip"
    RENAME = "rename"
    OVERWRITE = "overwrite"
    DELETE = "delete"


@dataclass(frozen=True)
class OrganizeFilesInput:
    source_dir: Path
    dry_run: bool = True
    conflict_strategy: ConflictStrategy = ConflictStrategy.SKIP
    recursive: bool = False
    max_files: int = MAX_FILES
    custom_map: dict[str, str] = field(default_factory=dict)


@dataclass
class OrganizationResult:
    organized: int = 0
    conflicts: int = 0
    skipped: int = 0
    overwritten: int = 0
    deleted: int = 0
    errors: int = 0
    categories: set[str] = field(default_factory=set)


@dataclass(frozen=True)
class DirectoryAnalysis:
    source_dir: Path
    file_count: int
    category_counts: dict[str, int]

    @property
    def categories(self) -> list[str]:
        return sorted(self.category_counts)
