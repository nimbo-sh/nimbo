import re

from rich.console import Console
from rich.theme import Theme

_console = Console(
    theme=Theme(
        {
            "step": "bold magenta",
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
    def step(current: int, out_of: int, msg):
        _console.print(f"[{current}/{out_of}]", style="step", end=" ")
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
