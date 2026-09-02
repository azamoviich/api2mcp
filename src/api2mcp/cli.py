from __future__ import annotations

import argparse
import sys

from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .generator import write_server
from .parser import parse_spec

console = Console()

BANNER = r"""[bold blue] _   _  ____   _____  __  __  _____ ____
| | | |___ \  |  ___||  \/  |/ ____|  _ \
| |_| | __) | | |_   | |\/| | |     | |_) |
|  _  |/ __/  |  _|  | |  | | |     |  __/
|_| |_|_____| |_|    |_|  |_|\_____|_|[/bold blue]"""


def _print_banner() -> None:
    console.print(BANNER)
    console.print("[dim]Turn any OpenAPI spec into a working MCP server[/dim]\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="api2mcp",
        description="Turn any OpenAPI spec into a working MCP server.",
    )
    parser.add_argument("source", help="OpenAPI spec URL or local file path (json or yaml)")
    parser.add_argument("-o", "--out", default="./mcp_server", help="Output directory (default: ./mcp_server)")
    parser.add_argument("-q", "--quiet", action="store_true", help="Suppress banner and table output")
    args = parser.parse_args()

    if not args.quiet:
        _print_banner()

    with console.status(f"[bold green]Fetching spec from {args.source} ...", spinner="dots"):
        try:
            spec = parse_spec(args.source)
        except Exception as exc:  # noqa: BLE001
            console.print(f"[bold red]error:[/bold red] failed to parse spec: {exc}")
            sys.exit(1)

    if not spec.operations:
        console.print("[bold red]error:[/bold red] no operations found in spec")
        sys.exit(1)

    out_file = write_server(spec, args.out)

    if not args.quiet:
        table = Table(title=f"Generated {len(spec.operations)} tools for '{spec.title}'", show_lines=False)
        table.add_column("Tool", style="cyan bold")
        table.add_column("Method", style="magenta")
        table.add_column("Path", style="white")
        table.add_column("Summary", style="dim")
        for op in spec.operations:
            table.add_row(op.func_name, op.method.upper(), op.path, op.summary or "-")
        console.print(table)

    run_cmd = f'cd {args.out} && pip install "mcp[cli]" requests && python server.py'
    console.print(
        Panel(
            Text.from_markup(
                f"[bold green]✓[/bold green] {out_file}\n"
                f"[bold green]✓[/bold green] {out_file.parent / 'README.md'}\n\n"
                f"[bold]Run it:[/bold]\n[cyan]{escape(run_cmd)}[/cyan]"
            ),
            title="[bold]Done[/bold]",
            border_style="green",
        )
    )


if __name__ == "__main__":
    main()
