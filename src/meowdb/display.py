from __future__ import annotations

import contextvars

from rich.console import Console

_console_var: contextvars.ContextVar[Console | None] = contextvars.ContextVar(
    "_console_var", default=None
)

ICON_ERROR = "[bold red]✗[/bold red]"
ICON_SUCCESS = "[bold green]✓[/bold green]"
ICON_WARNING = "[bold yellow]![/bold yellow]"
ICON_HINT = "[bold blue]→[/bold blue]"
ICON_INFO = "[dim]·[/dim]"


class _ConsoleProxy:
    """Thread-safe console proxy backed by a ContextVar."""

    def get(self) -> Console:
        c = _console_var.get()
        if c is None:
            c = Console()
            _console_var.set(c)
        return c

    def set(self, c: Console) -> None:
        _console_var.set(c)

    def print(self, *args: object) -> None:
        self.get().print(*args)


console = _ConsoleProxy()


def print_error(message: str) -> None:
    console.print(f"{ICON_ERROR} {message}")


def print_success(message: str) -> None:
    console.print(f"{ICON_SUCCESS} {message}")


def print_warning(message: str) -> None:
    console.print(f"{ICON_WARNING} {message}")


def print_hint(message: str) -> None:
    console.print(f"{ICON_HINT} {message}")


def print_info(message: str) -> None:
    console.print(f"{ICON_INFO} {message}")
