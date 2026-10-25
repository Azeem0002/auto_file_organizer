from pathlib import Path

from ..models.models import ValidationError


def validate_source_dir(path: Path, max_files: int, recursive: bool = False) -> Path:
    candidate = path.expanduser()
    absolute_candidate = candidate.absolute()
    if any(parent.is_symlink() for parent in [absolute_candidate, *absolute_candidate.parents]):
        raise ValidationError(f"Source directory path cannot contain symlinks: {candidate}")
    try:
        resolved = candidate.resolve(strict=True)
        home = Path.home().resolve(strict=True)
    except (OSError, RuntimeError) as error:
        raise ValidationError(f"Cannot access source directory: {error}") from error

    if not resolved.is_relative_to(home):
        raise ValidationError(f"Source directory must be inside your home directory: {candidate}")
    if not resolved.is_dir():
        raise ValidationError(f"Source path is not a directory: {candidate}")

    try:
        files = resolved.rglob("*") if recursive else resolved.iterdir()
        count = 0
        for item in files:
            if item.is_file():
                count += 1
                if count > max_files:
                    raise ValidationError(f"Directory exceeds the {max_files}-file limit.")
    except PermissionError as error:
        raise ValidationError(f"Cannot read source directory: {candidate}") from error
    except OSError as error:
        raise ValidationError(f"Cannot access source directory: {error}") from error

    return resolved
