from __future__ import annotations

import re
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from ..app.application import run_analyze, run_organize
from ..models.models import APP_CONFIG, ConflictStrategy, OrganizeFilesInput, ValidationError

app = typer.Typer(help="Organize and analyze local files")
console = Console()


def _parse_mappings(values: list[str]) -> dict[str, str]:
    mappings: dict[str, str] = {}
    for value in values:
        extension, separator, category = value.partition("=")
        extension, category = extension.strip().lower(), category.strip()
        if not separator or not re.fullmatch(r"\.[a-z0-9][a-z0-9._+-]*", extension):
            raise ValueError(f"Invalid mapping {value!r}; use .extension=Category")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 _-]*", category) or category in {".", ".."}:
            raise ValueError(f"Invalid category in mapping {value!r}.")
        mappings[extension] = category
    return mappings


@app.command()
def organize(
    source_dir: Path = typer.Argument(..., exists=True, file_okay=False, dir_okay=True),
    execute: bool = typer.Option(False, "--execute", help="Move files after confirmation"),
    strategy: ConflictStrategy = typer.Option(ConflictStrategy.SKIP, "--strategy"),
    recursive: bool = typer.Option(False, "--recursive"),
    max_files: int = typer.Option(APP_CONFIG.max_files, "--max-files", min=1, max=APP_CONFIG.max_files),
    mapping: list[str] = typer.Option([], "--map", help="Custom category mapping: .ext=Category"),
) -> None:
    try:
        request = OrganizeFilesInput(
            source_dir=source_dir.expanduser(),
            dry_run=not execute,
            conflict_strategy=strategy,
            recursive=recursive,
            max_files=max_files,
            custom_map=_parse_mappings(mapping),
        )
        if execute and not typer.confirm(f"Move up to {max_files} files from {source_dir}?", default=False):
            raise typer.Abort()
        result = run_organize(request)
        console.print("[bold]Preview complete. No files were changed.[/bold]" if not execute else "[bold green]Organization complete.[/bold green]")
        table = Table(title="Organization result")
        table.add_column("Measure")
        table.add_column("Count", justify="right")
        for label, count in (
            ("Organized", result.organized), ("Skipped", result.skipped),
            ("Conflicts", result.conflicts), ("Overwritten", result.overwritten),
            ("Deleted", result.deleted), ("Errors", result.errors),
        ):
            table.add_row(label, str(count))
        console.print(table)
    except typer.Abort:
        typer.echo("Operation cancelled.")
        raise typer.Exit(0)
    except (ValidationError, ValueError, OSError, RuntimeError) as error:
        typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(1)


@app.command()
def analyze(
    source_dir: Path = typer.Argument(..., exists=True, file_okay=False, dir_okay=True),
    max_files: int = typer.Option(50000, "--max-files", min=1),
) -> None:
    try:
        analysis = run_analyze(source_dir.expanduser(), max_files)
        summary = Table(title=f"Analysis: {analysis.source_dir}")
        summary.add_column("Measure")
        summary.add_column("Count", justify="right")
        summary.add_row("Files scanned", f"{analysis.file_count:,}")
        summary.add_row("Categories", str(len(analysis.categories)))
        console.print(summary)
        if analysis.categories:
            details = Table(title="Files by category")
            details.add_column("Category")
            details.add_column("Files", justify="right")
            details.add_column("Share", justify="right")
            for category in analysis.categories:
                count = analysis.category_counts[category]
                share = count / analysis.file_count * 100 if analysis.file_count else 0
                details.add_row(category, f"{count:,}", f"{share:.1f}%")
            console.print(details)
    except (ValidationError, ValueError, OSError, RuntimeError) as error:
        typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
