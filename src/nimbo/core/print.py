from rich.console import Console
from rich.theme import Theme

console = Console(
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
print = console.print
print_header = lambda x: console.print(f"[blue]==>[/blue] {x}", style="bold")
