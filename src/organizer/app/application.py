
from pathlib import Path

from ..models.models import OrganizeFilesInput, BackupCommandInput
from ..core.organize_service import organize_files, analyze_directory

def run_organize(input_data: OrganizeFilesInput):
    return organize_files(input_data)

def run_analyze(source_dir: Path, max_files: int):
    return analyze_directory(source_dir, max_files)

def run_backup(input_data: BackupCommandInput):
    pass

def list_backups(backup_dir: Path)-> list[Path]:
    pass

def run_restore(backup_path: Path, restore_dir: Path, backup_dir: Path) -> bool:
    pass