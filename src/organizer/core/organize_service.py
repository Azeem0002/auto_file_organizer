
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Iterator


from loguru import logger
from tqdm import tqdm


from ..core.file_utils import extract_file_category, gather_file_metadata, generate_unique_filename
from ..validators.validation import parse_source_dir_secure
from ..models.models import (
    DirectoryAnalysis,
    ConflictStrategy,
    OrganizeFilesInput,
    OrganizeOperationState,
    OrganizationResult,
    ORGANIZE_STATE_PATH,
    STATE_DIR,
    ValidationError
    )


def require_valid_source_dir(src_dir: Path, max_files: int)-> Path:

    validation = parse_source_dir_secure(src_dir, max_files)
    if validation.is_invalid:
        err_msg= "\n".join(str(e) for e in validation.errors)
        raise ValidationError(f"Invalid source directory: {err_msg}")

    value = validation.value
    if value is None:
        raise ValidationError("Source directory is unexpectedly None")
    return value


def _save_organize_state(state: OrganizeOperationState)-> None:
    """Persist crash recovery state for long running process"""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "source_dir": state.source_dir,
        "conflict_strategy": state.conflict_strategy,
        "recursive": state.recursive,
        "max_files": state.max_files,
        "started_at": state.started_at,
        "completed_paths": state.completed_paths,
    }
    temp_path = ORGANIZE_STATE_PATH.with_suffix(".tmp")
    temp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    temp_path.replace(ORGANIZE_STATE_PATH)

def _load_organize_state()-> OrganizeOperationState | None:
    """load last organize checkpoint"""

    if not ORGANIZE_STATE_PATH.exists():
        return None

    data = json.loads(ORGANIZE_STATE_PATH.read_text(encoding="utf-8"))
    return OrganizeOperationState(
        source_dir = str(data["source_dir"]),
        conflict_strategy = str(data["conflict_strategy"]),
        recursive=bool(data["recursive"]),
        max_files=int(data["max_files"]),
        started_at= str(data["started_at"]),
        completed_paths=[str(path) for path in data.get("completed_paths", [])],
    )

def _get_file_iterator(src_dir: Path, recursive: bool)-> Iterator[Path]:

    if recursive:
        return (item for item in src_dir.rglob("*") if item.is_file())
    return (item for item in src_dir.iterdir() if item.is_file())

def _collect_files_for_organization(src_dir: Path, recursive: bool, max_files: int)-> list[Path]:

    return list(_get_file_iterator(src_dir, recursive))[:max_files]

def _prepare_resume_state(
        validated_source: Path,
        input_data: OrganizeFilesInput,
    )-> tuple[OrganizeOperationState | None, set[str]]:

    if input_data.dry_run:
        return None, set()

    current_source = str(validated_source.resolve())
    existing_state = _load_organize_state()
    if existing_state is None:
        state = OrganizeOperationState(
            source_dir = current_source,
            conflict_strategy = input_data.conflict_strategy.value,
            recursive = input_data.recursive,
            max_files = input_data.max_files,
            started_at = datetime.now().isoformat(),
        )
        _save_organize_state(state)
        return state, set()

    if (
        existing_state.source_dir != current_source
        or existing_state.conflict_strategy != input_data.conflict_strategy.value
        or existing_state.recursive != input_data.recursive
        or existing_state.max_files != input_data.max_files
    ):
        raise ValidationError(
            "Existing crash recovery state does not match this organize run."
            "Clear or resume the previous run first. "
        )

    logger.info(
        f"Resuming previous organize run from from {existing_state.started_at}. "
        f"Already processed: {len(existing_state.completed_paths)} files. "
    )
    return existing_state, set(existing_state.completed_paths)


def _get_pending_files(
        all_files: list[Path],
        source_dir: Path,
        input_data: OrganizeFilesInput,
        completed_paths: set[str], 
    )-> list[Path]:

    if input_data.dry_run:
        return all_files

    return [
        file_path
        for file_path in all_files
        if str(file_path.relative_to(source_dir)) not in completed_paths
    ]


def _resolve_target_path(target_path: Path, strategy: ConflictStrategy)-> Path | None:

    if strategy is ConflictStrategy.SKIP:
        return None
    elif strategy is ConflictStrategy.RENAME:
        return generate_unique_filename(target_path)
    elif strategy is ConflictStrategy.OVERWRITE:
        target_path.unlink(missing_ok=True)
        return target_path

def _organize_single_file(
    file_path: Path,
    src_dir: Path,
    strategy: ConflictStrategy,
    created_categories: set[str],
    result: OrganizationResult,
    dry_run: bool,
    custom_mapping: dict[str, str] | None = None,        
)-> None:

    file_info = gather_file_metadata(file_path, custom_mapping)
    result.discovered_categories.add(file_info.category)

    category_dir = src_dir /file_info.category
    if file_info.category not in created_categories and not category_dir.exists():
        if not dry_run:
            category_dir.mkdir(exist_ok=True)
        created_categories.add(file_info.category)
        result.created_categories_count += 1

    if file_path.parent == category_dir:
        result.skipped += 1
        return

    target_path = category_dir / file_info.name
    if target_path.exists():
        if strategy is ConflictStrategy.DELETE:
            if not dry_run:
                file_path.unlink(missing_ok=True)
            result.organized += 1
            return

        resolved_target = _resolve_target_path(target_path, strategy)
        if resolved_target is None:
            result.conflicts += 1
            return
        target_path = resolved_target

    if not dry_run:
        shutil.move(str(file_path), str(target_path))
        result.operations.append((file_path, target_path))

    result.organized += 1


def _organize_with_error_logging(
        file_path: Path,
        source_dir: Path,
        input_data: OrganizeFilesInput,
        created_categories: set[str],
        result: OrganizationResult,
)-> bool:
    try:
        _organize_single_file(
            file_path=file_path,
            src_dir = source_dir,
            strategy=input_data.conflict_strategy,
            created_categories=created_categories,
            result=result,
            dry_run=input_data.dry_run,
            custom_mapping=input_data.custom_mapping,
        )
        return True
    
    except ValidationError as e:
        logger.error(f"Validation Failed for {file_path.name}: {e}")
        result.errors += 1
    except (OSError, RuntimeError) as e:
        logger.error(f"Failed to process {file_path.name}: {e}")
        result.errors += 1

    return False

def _mark_file_completed(
        state: OrganizeOperationState | None,
        completed_paths: set[str],
        relative_path: str,
        ) -> None:
    if state is None or relative_path in completed_paths:
        return

    completed_paths.add(relative_path)
    state.completed_paths.append(relative_path)
    _save_organize_state(state)

def _clear_organize_state()-> None:
    ORGANIZE_STATE_PATH.unlink(missing_ok=True)

def _log_organize_results(result: OrganizationResult, dry_run: bool)-> None:

    mode = "DRY RUN" if dry_run else "COMPLETE"

    logger.success(
        f"{mode}: {result.organized} organized, "
        f"{mode}: {result.skipped} skipped, "
        f"{mode}: {result.conflicts} conflicts, "
        f"{mode}: {result.errors} errors, "
    )
    if result.discovered_categories:
        logger.info(f"Categories: {", ".join(sorted(result.discovered_categories))}")





###### Public adapter #########
def organize_files(input_data: OrganizeFilesInput)-> OrganizationResult:

    validated_source = require_valid_source_dir(input_data.source_dir, input_data.max_files)
    state, completed_paths = _prepare_resume_state(validated_source, input_data)
    result = OrganizationResult()
    created_categories: set[str] = set()
    all_files = _collect_files_for_organization(validated_source, input_data.recursive, input_data.max_files)

    if not all_files:
        logger.info("No files to organize")
        _clear_organize_state()
        return result

    pending_files = _get_pending_files(all_files, validated_source, input_data, completed_paths)
    logger.info(f"Found {len(all_files)} files")
    logger.info(f"{len(pending_files)} files remaining to organize")

    # if state is not None and completed_paths:
    #     logger.info(f"Resuming with {len(pending_files)} files remaining")

    try:
        with tqdm(
            total = len(pending_files),
            desc="organizing",
            unit="files",
            colour="blue",
            bar_format= "{l_bar}{bar:40}{r_bar}",
            ncols=80,
            mininterval=0.1,
        ) as progress:
            
            for file_path in pending_files:
                relative_path = str(file_path.relative_to(validated_source))
                file_completed = _organize_with_error_logging(
                    file_path, validated_source, input_data, created_categories, result
                )
    
                if file_completed:
                    _mark_file_completed(state, completed_paths, relative_path)
                progress.update(1)
    except KeyboardInterrupt:
        logger.warning("Organization Interrupted. progress was saved for resume.")
        raise
    except Exception:
        logger.exception("Organization crashed. Progress was saved for resume.")
        raise

    else:
        if result.errors:
            logger.warning(
                "Organization completed with errors. Progress was saved to failed files"
                "can be retried."
            )
        else:
            _clear_organize_state()

    _log_organize_results(result, input_data.dry_run)
    return result


def analyze_directory(src_dir: Path, max_files: int)-> DirectoryAnalysis:

    validated_source = require_valid_source_dir(src_dir, max_files)
    file_count: int = 0
    category_counts: dict[str, int] = {}

    for item in validated_source.iterdir():
        if item.is_file():
            file_count += 1
            try:
                category = extract_file_category(item)
            except ValidationError:
                logger.warning("Some files could not be categorized")
                continue

            category_counts[category] = category_counts.get(category, 0) + 1

    return DirectoryAnalysis(
        source_dir= validated_source,
        file_count=file_count,
        category_counts=category_counts
    )
