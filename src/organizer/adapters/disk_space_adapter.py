
from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path


from loguru import logger

from ..models.models import DiskSpacePolicy



# Public use case
def get_disk_space_policy() -> DiskSpacePolicy:

    return DiskSpacePolicy(
        backup_buffer_percent=_positive_int_env("ORGANIZER_BACKUP_BUFFER_PERCENT", 20),
        minimum_free_percent=_positive_int_env("ORGANIZER_MINIMUM_FREE_PERCENT", 10),
        low_space_warning_percent=_positive_int_env("ORGANIZER_LOW_SPACE_WARNING_PERCENT", 5),
        maximum_exact_count=_positive_int_env("ORGANIZER_MAXIMUM_EXACT_FILE_COUNT", 100_000),
        maximum_backup_files=_positive_int_env("ORGANIZER_MAXIMUM_BACKUP_FILES", 1_000_000),
        dast_estimate_sample_size=_positive_int_env("ORGANIZER_FAST_ESTIMATE_SAMPLE_SIZE", 100),
    )
    