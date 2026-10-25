# Auto File Organizer

A local command-line tool that analyzes files and organizes them into category folders based on their extensions.

## Requirements

- Python 3.13 or newer
- [uv](https://docs.astral.sh/uv/)

## Install

From the project directory, install the project and its dependencies:

```sh
uv sync
```

This creates the project's `.venv`. Check the available commands:

```sh
uv run python -m organizer --help
```

## Quick start

### 1. Analyze a directory

Analysis is read-only. It reports file counts by category and does not accept `--execute`:

```sh
uv run python -m organizer analyze ~/Downloads
```

Analysis scans files directly inside the selected directory, not its subdirectories.

### 2. Preview the organization

Organizing is a dry run by default, so this command reports planned moves without changing files:

```sh
uv run python -m organizer organize ~/Downloads
```

### 3. Apply the organization

When the preview looks right, add `--execute`. The command asks for confirmation before moving files:

```sh
uv run python -m organizer organize ~/Downloads --execute
```

## Organize options

Each organize run is limited to 300 files. You can set a lower limit with `--max-files`. If the selected directory contains more files than that limit, the command stops before moving any files. With `--recursive`, the limit counts files in subdirectories too.

```sh
uv run python -m organizer organize ~/Downloads --max-files 100
uv run python -m organizer organize ~/Downloads --recursive
```

By default, files are skipped when a same-named file already exists in their category folder. Use `--strategy` to choose another collision behavior:

- `skip` — leave the incoming file in place (default)
- `rename` — give the incoming file a unique name
- `overwrite` — replace the existing destination file
- `delete` — delete the incoming source file when a same-named destination exists

Example:

```sh
uv run python -m organizer organize ~/Downloads --execute --strategy rename
```

Use `--map` to assign extensions to custom category folders. Repeat it for multiple extensions:

```sh
uv run python -m organizer organize ~/Downloads --map .log=Logs --map .epub=Books
```

Category names may contain letters, numbers, spaces, underscores, and hyphens. Extension matching ignores case.

## Analyze options

Analysis has a separate limit, defaulting to 50,000 files. Lower it with `--max-files`:

```sh
uv run python -m organizer analyze ~/Downloads --max-files 10000
```

## Run with Python directly

After `uv sync`, you can activate the project's environment and invoke the module with Python:

```sh
source .venv/bin/activate
python3 -m organizer analyze ~/Downloads
python3 -m organizer organize ~/Downloads
```

On Windows PowerShell, activate `.venv\Scripts\Activate.ps1` and use `python -m organizer ...`.

The installed command is also available as a shortcut:

```sh
uv run file-organizer --help
```

## Directory access and data

The source directory must exist, be readable, and be inside your home directory. Paths containing symbolic links are rejected. File analysis and organization happen locally; file contents are not uploaded.

## More help

```sh
uv run python -m organizer organize --help
uv run python -m organizer analyze --help
```
