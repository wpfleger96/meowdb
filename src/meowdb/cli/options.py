from __future__ import annotations

import click

db_path_option = click.option(
    "--db-path",
    type=click.Path(dir_okay=False, path_type=str),
    default=None,
    help="Override the default database file location.",
)
