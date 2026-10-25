import re
from pathlib import Path


_CATEGORY_MAP = {
    ".mp4": "Videos", ".avi": "Videos", ".mkv": "Videos", ".mov": "Videos",
    ".wmv": "Videos", ".flv": "Videos", ".webm": "Videos", ".m4v": "Videos",
    ".mp3": "Audios", ".wav": "Audios", ".flac": "Audios", ".m4a": "Audios",
    ".ogg": "Audios", ".aac": "Audios", ".wma": "Audios", ".opus": "Audios",
    ".jpg": "Images", ".jpeg": "Images", ".png": "Images", ".gif": "Images",
    ".webp": "Images", ".bmp": "Images", ".tiff": "Images", ".svg": "Images",
    ".ico": "Images", ".heic": "Images", ".raw": "Images",
    ".pdf": "Documents", ".doc": "Documents", ".docx": "Documents",
    ".txt": "Documents", ".rtf": "Documents", ".odt": "Documents", ".md": "Documents",
    ".xls": "Spreadsheets", ".xlsx": "Spreadsheets", ".ods": "Spreadsheets", ".csv": "Spreadsheets",
    ".ppt": "Presentations", ".pptx": "Presentations", ".odp": "Presentations", ".key": "Presentations",
    ".zip": "Archives", ".tar": "Archives", ".rar": "Archives", ".7z": "Archives",
    ".bz2": "Archives", ".gz": "Archives", ".tar.gz": "Archives", ".tar.bz2": "Archives",
    ".tar.xz": "Archives", ".tgz": "Archives",
    ".py": "Code", ".js": "Code", ".java": "Code", ".cpp": "Code", ".c": "Code",
    ".html": "Code", ".css": "Code", ".json": "Code", ".xml": "Code", ".yaml": "Code",
    ".yml": "Code", ".toml": "Code", ".ini": "Code", ".cfg": "Code", ".conf": "Code",
    ".exe": "Executables", ".msi": "Executables", ".app": "Executables", ".sh": "Executables",
    ".bat": "Executables", ".cmd": "Executables",
}


def extract_file_category(file_path: Path, custom_map: dict[str, str] | None = None) -> str:
    if file_path.name.startswith("."):
        return "Hidden"

    suffixes = file_path.suffixes
    if not suffixes:
        return "No extension"

    compound_extension = "".join(suffixes).lower()
    last_extension = suffixes[-1].lower()
    mapping = {key.lower(): value for key, value in (custom_map or {}).items()}
    if compound_extension in mapping:
        category = mapping[compound_extension]
    elif last_extension in mapping:
        category = mapping[last_extension]
    else:
        category = _CATEGORY_MAP.get(compound_extension) or _CATEGORY_MAP.get(last_extension)

    if category is None:
        suffix_name = "".join(suffix.lstrip(".") for suffix in suffixes)
        category = re.sub(r"[^\w -]", "_", suffix_name).strip() or "Misc"

    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 _-]*", category) or category in {".", ".."}:
        raise ValueError(f"Unsafe category name: {category!r}")
    return category
