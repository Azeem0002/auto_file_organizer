
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
from ..adapters.filesystem_adapter import gather_file_metadata


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

    data= json.loads(ORGANIZE_STATE_PATH.read_text(encoding="utf-8"))
    return OrganizeOperationState(
        source_dir=str(data["source_dir"]),
        conflict_strategy=str(data["conflict_strategy"]),
        recursive=bool(data["recursive"]),
        max_files=int(data["max_files"]),
        started_at=str(data["started_at"]),
        completed_paths=[str(path) for path in data.get("completed_paths", [])],
    )

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

def _organize_single_file(
        file_path: Path,
        source_dir: Path,
        strategy: ConflictStrategy,
        created_categories: set[str],
        result: OrganizationResult,
        dry_dun: bool,
        custom_mapping: dict[str, str] | None = None,
)-> None:
    file_info= gather_file_metadata()




def _organize_with_error_logging(
        file_path: Path,
        source_dir: Path,
        Input_data: OrganizeFilesInput,
        created_categories: set[str],
        result: OrganizationResult
)-> bool:
    try:
        _organize_single_file(

        )

########Use case#######
def organize_files(input_data: OrganizeFilesInput)-> OrganizationResult:

    validated_source = _require_valid_source_dir(input_data.source_dir, input_data.max_files)
    state, completed_paths = _prepare_resume_state(validated_source, input_data)
    result = OrganizationResult()

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

                file_completed= _organize_with_error_logging()