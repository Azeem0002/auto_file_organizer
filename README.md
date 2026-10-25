# Auto File Organizer

A local command-line tool that classifies files by extension, previews or applies file moves, and summarizes the files in a directory.

## Requirements

- Python 3.13 or newer
- [uv](https://docs.astral.sh/uv/)

## Install

Open a terminal in the project directory and run:

```sh
uv sync
```

This creates the project environment and installs its dependencies. Check that the commands are available:

```sh
uv run file-organizer --help
```

You can also start the CLI through the project launcher:

```sh
uv run python main.py --help
```

## Analyze a directory

Show a summary and file counts by category without changing files:

```sh
uv run file-organizer analyze ~/Downloads
```

Analysis scans files directly inside the selected directory; it does not scan subdirectories. The default limit is 50,000 files. To choose a lower limit:

```sh
uv run file-organizer analyze ~/Downloads --max-files 10000
```

## Preview and organize files

Organizing is a dry run by default. It reports the planned results and leaves files in place:

```sh
uv run file-organizer organize ~/Downloads
```

To apply the moves, add `--execute`. The command asks for confirmation first:

```sh
uv run file-organizer organize ~/Downloads --execute
```

An organize run can process at most 300 files. The default is 300; lower it with `--max-files`. The source directory must contain no more than the selected limit, or the command stops before moving files. The limit applies across subdirectories when `--recursive` is enabled.

```sh
uv run file-organizer organize ~/Downloads --max-files 100
uv run file-organizer organize ~/Downloads --recursive --execute
```

By default, files with the same name in a category folder are skipped. Choose another collision behavior with `--strategy`:

- `skip` — keep the existing destination and leave the source file in place (default)
- `rename` — give the incoming file a unique name
- `overwrite` — replace the existing destination file
- `delete` — delete the incoming source file when a destination with the same name exists

Example:

```sh
uv run file-organizer organize ~/Downloads --execute --strategy rename
```

## Custom categories

Use `--map` to assign an extension to a category folder. You can provide the option more than once:

```sh
uv run file-organizer organize ~/Downloads --map .log=Logs --map .epub=Books
```

Category names may contain letters, numbers, spaces, underscores, and hyphens. Extensions are matched without regard to case.

## Directory access

For safety, source directories must exist, be readable, and be inside your home directory. Paths containing symbolic links are rejected. The organizer works on local files; it does not upload file contents.

## Available commands

```sh
uv run file-organizer --help
uv run file-organizer organize --help
uv run file-organizer analyze --help
```
