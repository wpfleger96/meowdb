from __future__ import annotations

import click

from meowdb.config import HOST, PORT


@click.command()
@click.option("--host", default=HOST, show_default=True, help="Bind address.")
@click.option("--port", default=PORT, show_default=True, type=int, help="Port number.")
@click.option("--reload", is_flag=True, default=False, help="Enable auto-reload for development.")
def serve(host: str, port: int, reload: bool) -> None:
    """Start the MeowDB web server."""
    import uvicorn

    uvicorn.run(
        "meowdb.api.app:create_app",
        factory=True,
        host=host,
        port=port,
        reload=reload,
    )
