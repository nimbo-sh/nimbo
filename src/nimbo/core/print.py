import re

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
            "step": "bold magenta",
            "step-number": "bold cyan",
            "info": "bold white",
            "warning": "bold yellow",
            "error": "bold red",
            "success": "bold green",
        }
    )
)


# TODO: replace / remove
nprint = _console.print


# TODO: replace / remove
def nprint_header(x) -> None:
    nprint(f"[blue]==>[/blue] {x}", style="bold")


# TODO: replace all printing with this model
class NimboPrint:
    @staticmethod
    def _format(msg: str) -> str:
        return re.sub("( |\\s)+", " ", msg).strip(" ")

    @staticmethod
    def step(curr: int, out_of: int, msg):
        _console.print(
            f"[[step-number]{curr}[/step-number]/[step-number]{out_of}[/step-number]]",
            style="step",
            end=" ",
        )
        print(NimboPrint._format(msg))

    @staticmethod
    def info(msg: str) -> None:
        _console.print("info", style="info", end=" ")
        print(NimboPrint._format(msg))

    @staticmethod
    def warning(msg: str) -> None:
        _console.print("warning", style="warning", end=" ")
        print(NimboPrint._format(msg))

    @staticmethod
    def error(msg: str) -> None:
        _console.print("error", style="error", end=" ")
        print(NimboPrint._format(msg))

    @staticmethod
    def success(msg: str) -> None:
        _console.print("success", style="success", end=" ")
        print(NimboPrint._format(msg))
