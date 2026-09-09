
import json
from datetime import datetime
from pathlib import Path
from typing import Iterator
from itertools import islice

from loguru import logger
from tqdm import tqdm

from ..models.models import ValidationError
from ..validators.validation import parse_source_dir_secure
from ..models.models import (OrganizeFilesInput, OrganizationResult, OrganizeOperationState, ConflictStrategy, ORGANIZE_STATE_PATH, STATE_DIR)
from ..adapters.filesystem_adapter import gather_file_metadata, generate_unique_filename, move_file


def _require_valid_source_dir(source_dir: Path, max_files: int)-> Path:

    source_validation= parse_source_dir_secure(source_dir)
    if source_validation.is_invalid:
        errors = '\n'.join(str(error) for error in source_validation.errors)
        raise ValidationError(f"Source Validation is invalid: \n{errors}")

    value = source_validation.value
    if value is None:
        raise ValidationError(f"Source directory cannot be None after validation ")
    return value

def _load_organization_state()-> OrganizeOperationState | None:

    if not ORGANIZE_STATE_PATH.exists():
        return None

    data = json.loads(ORGANIZE_STATE_PATH.read_text(encoding="utf-8"))

    try:
        return OrganizeOperationState(
            source_dir=str(data["source_dir"]),
            conflict_strategy=str(data["conflict_strategy"]),
            recursive=bool(data["recursive"]),
            max_files=int(data["max_files"]),
            started_at=str(data["started_at"]),
            completed_paths=[str(path) for path in data.get("completed_paths", [])],
        )
    except (KeyError, TypeError) as e:
        raise ValidationError(f"Missing key: {str(e)}") from e


def _save_organize_state(state: OrganizeOperationState)-> None:

    STATE_DIR.mkdir(parents=True, exist_ok=True)
    payload= {
        "source_die": state.source_dir,
        "conflict_strategy": state.conflict_strategy,
        "recursive": state.recursive,
        "max_files": state.max_files,
        "started_at": state.started_at,
        "completed_paths": state.completed_paths
    }

    temp_path= ORGANIZE_STATE_PATH.with_suffix(".tmp")
    temp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    temp_path.replace(ORGANIZE_STATE_PATH)


def _prepare_resume_state(
    validated_source: Path,
    input_data: OrganizeFilesInput   
    )-> tuple[OrganizeOperationState | None, set[str]]:

    if input_data.dry_run:
        return None, set()
    
    current_state= str(validated_source.resolve())
    existing_state= _load_organization_state()
    if existing_state is None:
        state= OrganizeOperationState(
            source_dir= current_state,
            conflict_strategy=input_data.conflict_strategy.value,
            recursive=input_data.recursive,
            max_files=input_data.max_files,
            started_at=datetime.now().isoformat()
        ) 
        _save_organize_state(state)
        return state, set()

    if (
        existing_state.source_dir != current_state
        or existing_state.conflict_strategy != input_data.conflict_strategy 
        or existing_state.recursive != input_data.recursive
        or existing_state.max_files != input_data.max_files
    ):
        raise ValidationError(
            "Existing crash recovery state doesn't match this organize run"
            "Clear or resume the previous run first"
        )

    logger.info(
        f"Resuming previous organize run from {existing_state}"
        f"Already processed: {len(existing_state.completed_paths)}"
    )
    return existing_state, set(existing_state.completed_paths) 

def _get_file_iterator(source_dir: Path, recursive: bool)-> Iterator[Path]:
    if recursive:
        return (item for item in source_dir.rglob("*") if item.is_file())
    return (item for item in source_dir.iterdir() if item.is_file())

def _collect_files_for_organization(source_dir: Path, recursive: bool, max_files)-> list[Path]:
    return list(islice(_get_file_iterator(source_dir, recursive), max_files))

def _clear_organize_state()-> None:
    return ORGANIZE_STATE_PATH.unlink(missing_ok=True)


def _get_pending_files(
        all_files: list[Path],
        source_dir: Path,
        input_data: OrganizeFilesInput,
        completed_paths: set[str]
)-> list[Path]:
    if input_data.dry_run:
        return all_files
  
    return [
        file_path
        for file_path in all_files
        if str(file_path.relative_to(source_dir)) not in completed_paths
    ]

def _resolve_conflicting_strategy_path(
        strategy: ConflictStrategy, 
        target_path: Path,  
        dry_run: bool)-> Path |None:

    if strategy == ConflictStrategy.SKIP:
        return None

    if strategy == ConflictStrategy.RENAME:
        return generate_unique_filename(target_path)

    if strategy == ConflictStrategy.OVERWRITE:
        if not dry_run:
            target_path.unlink(missing_ok=True)
        return target_path

    raise ValueError(f"Conflict strategy resolution doesn't support strategy: {strategy.value}")

    
def _organize_single_file(
        file_path: Path,
        source_dir: Path,
        strategy: ConflictStrategy,
        created_categories: set[str],
        result: OrganizationResult,
        dry_run: bool,
        custom_map: dict[str, str] | None = None,
)-> None:
    file_info= gather_file_metadata(file_path, custom_map)
    result.discovered_categories.add(file_info.category)

    category_dir = source_dir / file_info.category

    if file_info.category not in created_categories and not category_dir.exists():
        if not dry_run:
            category_dir.mkdir(exist_ok=True)
        created_categories.add(file_info.category)
        result.created_categories_count += 1

    if file_path.parents == category_dir:
        result.skipped += 1
        return

    target_path = category_dir / file_info.name
    if target_path.exists():
        if strategy == ConflictStrategy.DELETE:
            if not dry_run:
                file_path.unlink(missing_ok=True)
            result.organized += 1
            return

        resolved_target = _resolve_conflicting_strategy_path(strategy, target_path, dry_run=dry_run)
        if resolved_target is None:
            result.conflicts += 1
            return
        target_path = resolved_target

    if not dry_run:
        move_file(file_path, target_path)
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
            source_dir=source_dir,
            strategy=input_data.conflict_strategy,
            created_categories=created_categories,
            result=result,
            dry_run=input_data.dry_run,
            custom_map=input_data.custom_map
        )
        return True
    except ValidationError as e:
        logger.error(f"Validation failed for {file_path.name}: {str(e)}")
        result.errors += 1

    except (PermissionError, OSError, RuntimeError) as e:
        logger.error(f"Failed to process {file_path.name}: {str(e)}")
        result.errors += 1

    return False


########Use case#######
def organize_files(input_data: OrganizeFilesInput)-> OrganizationResult:

    validated_source = _require_valid_source_dir(input_data.source_dir, input_data.max_files)
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
    logger.info(f"{len(pending_files)} files remaining")

    try:
        with tqdm(
            total=len(pending_files),
            desc= "Organizing",
            unit="files",
            colour="blue",
            bar_format="{l_bar}{bar: 40}{r_bar}",
            ncols=80,
            mininterval=0.1
        ) as progress:
            for file_path in pending_files:
                relative_path = str(file_path.relative_to(validated_source))

                file_completed = _organize_with_error_logging(
                    file_path, validated_source, input_data, created_categories, result
                )

                if file_completed:
                    _mark_