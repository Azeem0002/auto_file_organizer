from pathlib import Path

from ..core.organize_service import analyze_directory, organize_files
from ..models.models import APP_CONFIG, DirectoryAnalysis, OrganizeFilesInput, OrganizationResult, ValidationError


def run_organize(input_data: OrganizeFilesInput) -> OrganizationResult:
    if input_data.max_files > APP_CONFIG.max_files:
        raise ValidationError(f"This installation can organize at most {APP_CONFIG.max_files} files per run.")
    return organize_files(input_data)


def run_analyze(source_dir: Path, max_files: int = 50000) -> DirectoryAnalysis:
    return analyze_directory(source_dir, max_files)
