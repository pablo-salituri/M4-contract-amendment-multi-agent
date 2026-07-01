import sys

from rich.console import Console
from rich.theme import Theme

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

_THEME = Theme(
    {
        "info": "dim",
        "success": "green",
        "error": "bold red",
        "title": "bold blue",
        "step": "cyan",
        "path": "white",
    }
)

console = Console(theme=_THEME)
err_console = Console(theme=_THEME, stderr=True)
