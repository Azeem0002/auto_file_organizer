
from pathlib import Path

from ..models.models import OrganizeFilesInput, BackupCommandInput
from ..adapters.hosted_entitlement_adapter import fetch_hosted_entitlement

def organize_file_limit(user_email: str | None)-> int:

    del user_email
    entitlement = fetch_hosted_entitlement()
    if entitlement is not None:
        max_files_per_run = entitlement.get("max_files_per_run")
        if isinstance(max_files_per_run, int) and max_files_per_run > 0:
            return max_files_per_run
    return get_subscription_plan(SubscriptionTier.FREE).max_files_per_run


def run_organize(input_data: OrganizeFilesInput, *, user_email: str | None= None)-> None:

    allowed_files = organize_file_limit(user_email)
    if input_data.max_files > allowed_files:
        raise ValueError(
            f"This account can organize up to {allowed_files} files per run. "
            "Choose a lower --max-files value or upgrade your plan."
        )
    return organize_files(input_data)