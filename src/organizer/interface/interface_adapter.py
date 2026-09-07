
PROJECT_NAME = "file_organizer"

def _get_frontend_contract() -> dict:

    return {
        "project": PROJECT_NAME,
        "frontend_rule": "Build any frontend you want, but do not duplicate path validation, backup rules, conflict handling, or organize logic in the UI.",
        "primary_boundary": "CLI now; small desktop or web PWA frontend can replace it later.",
        "commands": [
            "python organizer.py organize /path/to/source_dir",
            "python organizer.py organize /path/to/source_dir --execute --strategy <skip|rename|overwrite|delete>",
            "python organizer.py organize /path/to/source_dir --recursive --max-files 10000",
            "python organizer.py organize /path/to/source_dir --map .mp4=recordings",
            "python organizer.py organize /path/to/source_dir --execute --backup",
            "python organizer.py backup /path/to/source_dir",
            "python organizer.py backup /path/to/source_dir --list",
            "python organizer.py backup /path/to/source_dir --restore /path/to/archive.zip --restore-to /path/to/destination",
            "python organizer.py analyze /path/to/source_dir",
            "python organizer.py interactive",
        ],
        "organize_request": {
            "source_dir": "required filesystem path",
            "dry_run_default": True,
            "conflict_strategies": ["skip", "rename", "overwrite", "delete"],
            "optional_choices": ["recursive", "max_files", "backup", "custom extension mapping"],
        },
        "main_use_cases": [
            "organize files into categories",
            "create backups before risky operations",
            "restore archive backups",
            "analyze directory before mutating it"
        ],
        "display": "Show the current action, confirmation prompts, warnings, and final counts. Keep filesystem details visible because this app is operator-facing.",
        "safety_note": "Protect against destructive file actions by keeping confirmations at the boundary and preserving dry-run behavior by default.",
        "frontend_must_send": [
            "absolute or user-resolved filesystem paths",
            "explicit confirmation before destructive operations",
            "clear conflict strategy selection",
        ],
        "backend_enforces": [
            "validation for missing, unsafe, or unauthorized paths",
            "permission and filesystem failure detection",
            "dry-run versus execute behavior",
            "backup outcome before a destructive organize run continues",
        ],
        "frontend_should_present": [
            "backend validation, permission, and filesystem error messages",
            "dry-run versus execute mode clearly before confirmation",
            "backup success or failure and the available next action",
        ],
        "billing_configuration": {
            "default_plan_file": "billing_plans.json",
            "override_environment_variable": "ORGANIZER_BILLING_CONFIG",
            "subscription_store_override": "ORGANIZER_SUBSCRIPTION_STORE",
            "rule": "Edit plan prices and max_files_per run in configuration; do nit change python source for commercial limits."
        }
    }

def get_frontend_contract()-> dict:
    """Public wrapper for the frontend/back-end handoff contract."""
    return _get_frontend_contract()
