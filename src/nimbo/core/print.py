from rich.console import Console
from rich.theme import Theme

_console = Console(
    theme=Theme(
        {
            "repr.number": "",
            "repr.str": "",
            "repr.ellipsis": "",
            "repr.eui48": "",
            "repr.eui64": "",
            "repr.ipv4": "",
            "repr.ipv6": "",
            "repr.filename": "",
            "repr.path": "",
            "error": "bold red",
            "warning": "bold magenta",
        }
    )
)
nprint = _console.print


def nprint_header(x) -> None:
    nprint(f"[blue]==>[/blue] {x}", style="bold")
