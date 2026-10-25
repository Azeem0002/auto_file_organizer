import shutil
from pathlib import Path


def unique_destination(path: Path) -> Path:
    for number in range(1, 1001):
        candidate = path.with_name(f"{path.stem}_{number}{path.suffix}")
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"Could not find an unused name for {path.name}.")


def move_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(source), str(destination))
