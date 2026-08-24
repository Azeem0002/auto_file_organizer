
import re
from datetime import datetime
from pathlib import Path

from ..models.models import FileInfo, ValidationError


def extract_file_category(file_path: Path, custom_mapping: dict[str, str] | None = None)-> str:
    "Create file categories"

    # get hidden files
    if file_path.name.startswith("."):
        return "Hidden"

    # Get all suffixes
    file_suffixes = file_path.suffixes
    if not file_suffixes:
        return "No_extension"

    compound_extension = "".join(file_suffixes).lower()
    last_extension = file_suffixes[-1].lower()


    # custom user mapping overrides built in defaults
    custom_mapping = custom_mapping or {}

    if compound_extension in custom_mapping:
        return custom_mapping[compound_extension]
    if last_extension in custom_mapping:
        return custom_mapping[last_extension]

    
    category_map = {
        ".mp4": "Videos", ".avi": "Videos", ".mkv": "Videos",
        ".mov": "Videos", ".wmv": "Videos", ".flv": "Videos",
        ".webm": "Videos", ".m4v": "Videos",
        ".mp3": "Audios", ".wav": "Audios", ".flac": "Audios",
        ".m4a": "Audios", ".ogg": "Audios", ".aac": "Audios",
        ".wma": "Audios", ".opus": "Audios",
        ".jpg": "Images", ".jpeg": "Images", ".png": "Images",
        ".gif": "Images", ".webp": "Images", ".bmp": "Images",
        ".tiff": "Images", ".svg": "Images", ".ico": "Images",
        ".heic": "Images", ".raw": "Images",
        ".pdf": "Documents",
        ".doc": "Documents", ".docx": "Documents",
        ".txt": "Documents", ".rtf": "Documents",
        ".odt": "Documents", ".md": "Documents",
        ".pages": "documents",
        ".xls": "Spreadsheets", ".xlsx": "Spreadsheets",
        ".ods": "Spreadsheets", ".csv": "Spreadsheets",
        ".ppt": "Presentations", ".pptx": "Presentations",
        ".odp": "Presentations", ".key": "Presentations",
        ".zip": "Archives", ".tar": "Archives",
        ".rar": "Archives", ".7z": "Archives",
        ".bz2": "Archives", ".gz": "Archives",
        ".tar.gz": "Archives", ".tar.bz2": "Archives",
        ".tar.xz": "Archives", ".tgz": "Archives",
        ".py": "Code", ".js": "Code", ".java": "Code",
        ".cpp": "Code", ".c": "Code", ".html": "Code",
        ".css": "Code", ".json": "Code", ".xml": "Code",
        ".yaml": "Code", ".yml": "Code", ".toml": "Code",
        ".ini": "Code", ".cfg": "Code", ".conf": "Code",
        ".exe": "Executables", ".msi": "Executables",
        ".app": "Executables", ".sh": "Executables",
        ".bat": "Executables", ".cmd": "Executables",
    }

    if compound_extension in category_map:
        return category_map[compound_extension]
    if last_extension in category_map:
        return category_map[last_extension]

    fallback_category = "".join(s.lstrip() for s in file_suffixes) if len(file_suffixes) > 1 else last_extension.lstrip(".")
    # Used as fallback when no dictionary match exists

    category = re.sub(r"[^\w\-]", "_", fallback_category)

    if not category or category.isspace():
        # for categories without extensions, use miscellaneous
        return "Misc"

    return category.strip()


def gather_file_metadata(file_path: Path, custom_mapping: dict[str, str] | None = None) -> FileInfo:

    if not file_path.is_file():
        raise ValidationError(f"Not a file: {file_path}")

    try:
        stat = file_path.stat() # file metadata statistic
    except (PermissionError, OSError) as e:
        raise ValidationError(f"Cannot read file metadata: {file_path}") from e

    return FileInfo(
        path = file_path,
        name = file_path.name,
        stem = file_path.stem,
        suffix = file_path.suffix,
        category = extract_file_category(file_path, custom_mapping),
        size = stat.st_size,
        mode = stat.st_mode,
        modified = datetime.fromtimestamp(stat.st_mtime)
    )

def generate_unique_filename(target_path: Path, max_attempts: int = 1000)-> Path:

    counter = 1
    parent = target_path.parent
    stem, suffix = target_path.stem, target_path.suffix

    while counter <= max_attempts:
        new_name = parent / f"{stem}_{counter}{suffix}"
        if not new_name.exists():
            return new_name
        counter += 1

    raise ValidationError(f"Could not generate unique file name after {max_attempts} attempts.")    

