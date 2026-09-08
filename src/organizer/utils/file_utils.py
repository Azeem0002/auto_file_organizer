
import re
from pathlib import Path

def extract_file_category(file_path: Path, custom_map: dict[str, str] | None= None)-> str:

    if file_path.name.startswith("."):
        return "hidden"

    file_suffixes= file_path.suffixes
    if not file_suffixes:
        return "no_extension"

    compound_extension = "".join(file_suffixes).lower()
    last_extension = file_suffixes[-1].lower()

    custom_map = custom_map or {}

    if compound_extension in custom_map:
        return custom_map[compound_extension]
    elif last_extension in custom_map:
        return custom_map[last_extension]

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
    elif last_extension in category_map:
        return category_map[last_extension]
    
    fallback_category = "".join(s.lstrip(".") for s in file_suffixes) if len(file_suffixes) > 1 else last_extension.lstrip(".")
    category= re.sub(r"[^\w\-]", "_", fallback_category)

    if not category or category.isspace():
        return "misc"
    return category.strip()