from itertools import islice
from pathlib import Path

from ..adapters.filesystem_adapter import move_file, unique_destination
from ..models.models import (
    APP_CONFIG,
    ConflictStrategy,
    DirectoryAnalysis,
    OrganizeFilesInput,
    OrganizationResult,
    ValidationError,
)
from ..utils.file_utils import extract_file_category
from ..validators.validation import validate_source_dir


def _files(source: Path, recursive: bool):
    candidates = source.rglob("*") if recursive else source.iterdir()
    return (path for path in candidates if path.is_file())


def analyze_directory(source_dir: Path, max_files: int = 50000) -> DirectoryAnalysis:
    if max_files < 1:
        raise ValidationError("Maximum files must be greater than zero.")
    source = validate_source_dir(source_dir, max_files)
    counts: dict[str, int] = {}
    files = 0
    for path in _files(source, recursive=False):
        files += 1
        try:
            category = extract_file_category(path)
        except ValueError:
            continue
        counts[category] = counts.get(category, 0) + 1
    return DirectoryAnalysis(source, files, counts)


def organize_files(input_data: OrganizeFilesInput) -> OrganizationResult:
    if not 1 <= input_data.max_files <= APP_CONFIG.max_files:
        raise ValidationError(f"Organize runs must process between 1 and {APP_CONFIG.max_files} files.")
    source = validate_source_dir(input_data.source_dir, input_data.max_files, input_data.recursive)
    result = OrganizationResult()
    selected = list(islice(_files(source, input_data.recursive), APP_CONFIG.max_files))

    for path in selected:
        try:
            category = extract_file_category(path, input_data.custom_map)
            result.categories.add(category)
            category_dir = source / category
            if path.parent == category_dir:
                result.skipped += 1
                continue
            destination = category_dir / path.name
            if destination.exists():
                result.conflicts += 1
                if input_data.conflict_strategy is ConflictStrategy.SKIP:
                    result.skipped += 1
                    continue
                if input_data.conflict_strategy is ConflictStrategy.DELETE:
                    if not input_data.dry_run:
                        path.unlink()
                    result.deleted += 1
                    continue
                if input_data.conflict_strategy is ConflictStrategy.RENAME:
                    destination = unique_destination(destination)
                elif input_data.conflict_strategy is ConflictStrategy.OVERWRITE and not input_data.dry_run:
                    destination.unlink()
                    result.overwritten += 1
            if not input_data.dry_run:
                move_file(path, destination)
            result.organized += 1
        except (OSError, RuntimeError, ValueError) as error:
            result.errors += 1

    return result
