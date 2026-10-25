# File Organizer

A local command-line tool that previews or organizes files by category and reports directory contents.

## Commands

```sh
uv run file-organizer --help
uv run file-organizer analyze ~/Downloads
uv run file-organizer organize ~/Downloads
uv run file-organizer organize ~/Downloads --execute
```

Organizing defaults to a dry run. `--execute` asks for confirmation before moving files. Each organize run is limited to 300 files. Use `--recursive` to include subdirectories and `--map .ext=Category` to define a category for an extension.
