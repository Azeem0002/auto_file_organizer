
import shutil
from datetime import datetime
from pathlib import Path

from ..models.models import FileInfo, ValidationError
from ..utils.file_utils import extract_file_category


def gather_file_metadata(file_path: Path, custom_map: dict[str, str] | None =None)-> FileInfo:

    if not file_path.exists():
        raise ValidationError(f"Not a valid file: {file_path}")

    try:
        stat = file_path.stat()
    except (PermissionError, OSError) as e:
        raise ValidationError(f"Cannot read file metadata: {file_path}") from e

    return FileInfo(
        path=file_path,
        name=file_path.name,
        stem=file_path.stem,
        suffix =file_path.suffix,
        category=extract_file_category(file_path, custom_map),
        size=stat.st_size,
        mode=stat.st_mode,
        modified=datetime.fromtimestamp(stat.st_mtime)
    )

def generate_unique_filename(target_path: Path, max_attempts: int= 1000)-> Path:

    parent = target_path.parent
    name = target_path.name
    suffix= target_path.suffix

    for counter in range(1, max_attempts + 1):
        candidate = parent / f"{name}{counter}{suffix}"
        if not candidate.exists():
            return candidate

    raise RuntimeError(f"Cannot generate a unique filename after {max_attempts} attempts")

def move_file(source_path: Path, dest_path: Path)-> None:
    shutil.move(source_path, dest_path)