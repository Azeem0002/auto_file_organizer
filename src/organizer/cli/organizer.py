#!/usr/bin/env python3

import re
from datetime import datetime
from pathlib import Path

import typer 
from rich.console import Console
from rich .table import Table

from ..app.application import  list_backups as list

app = typer.Typer(
    help="Production File Organizer with Backup System"
)