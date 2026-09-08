
import shutil
from datetime import datetime
from pathlib import Path

from ..models.models import FileInfo, ValidationError
from ..utils.file_utils import extract_file_category


def gather_file_metadata(file_path: Path,custom_ma: dict[str, str] | None= None)-> FileInfo:

    if not file_path.is_file():
        raise ValidationError(f"Not a valid file: {file_path}")

    try:
        stat = file_path.stat()
    except (PermissionError, OSError):
        raise ValidationError("Cannot read file")