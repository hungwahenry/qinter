"""
qinter/cli/commands/list.py
List command for Qinter CLI.

Shows installed explanation packs and their details.
"""

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.columns import Columns
from qinter.packages.manager import get_package_manager


@click.command()
@click.option('--detailed', '-d', is_flag=True, help='Show detailed information')
@click.option('--by-type', '-t', help='Filter by exception type (e.g., NameError)')
def list_packs(detailed: bool, by_type: str):
    """
    List installed explanation packs.
    
    Examples:
        qinter list
        qinter list --detailed
        qinter list --by-type NameError
    """
    console = Console()
    manager = get_package_manager()
    
    # Get installed packs
    installed_packs = manager.list_installed_packs()
    
    if not installed_packs:
        _display_no_packs_message(console)
        return
    
    # Filter by type if specified
    if by_type:
        installed_packs = [
            pack for pack in installed_packs 
            if by_type in pack.get('targets', [])
        ]
        
        if not installed_packs:
            console.print(f"❌ No packs found that handle {by_type} exceptions")
            return
    
    # Display header
    _display_list_header(console, len(installed_packs), by_type)
    
    if detailed:
        _display_detailed_list(console, installed_packs)
    else:
        _display_compact_list(console, installed_packs)
    
    # Display summary
    _display_list_summary(console, installed_packs)


def _display_no_packs_message(console: Console):
    """Display message when no packs are installed."""
    message = Text.assemble(
        ("📦 ", "bold yellow"),
        ("No explanation packs installed\n\n", "bold white"),
        ("Get started by installing some packs:\n", "white"),
        ("  qinter install requests\n", "cyan"),
        ("  qinter install pandas numpy\n", "cyan"),
        ("  qinter search http\n", "cyan")
    )
    
    panel = Panel(
        message,
        title="[bold white]Qinter Package Manager",
        border_style="yellow",
        padding=(1, 2)
    )
    
    console.print(panel)


def _display_list_header(console: Console, count: int, filter_type: str):
    """Display list header."""
    header_text = Text()
    header_text.append("📋 ", style="bold cyan")
    header_text.append("Installed Explanation Packs", style="bold white")
    
    if filter_type:
        subtitle = Text()
        subtitle.append(f"Filtered by: ", style="white")
        subtitle.append(filter_type, style="yellow")
        subtitle.append(f" ({count} packs)", style="dim white")
        content = Text.assemble(header_text, "\n", subtitle)
    else:
        subtitle = Text()
        subtitle.append(f"Total: ", style="white")
        subtitle.append(str(count), style="bold yellow")
        subtitle.append(" packs", style="white")
        content = Text.assemble(header_text, "\n", subtitle)
    
    panel = Panel(
        content,
        border_style="cyan",
        padding=(1, 2)
    )
    
    console.print(panel)
    console.print()


def _display_compact_list(console: Console, packs: list):
    """Display compact list of packs."""
    table = Table(
        show_header=True,
        header_style="bold cyan",
        border_style="dim white",
        padding=(0, 1)
    )
    
    table.add_column("Pack Name", style="yellow", width=25)
    table.add_column("Version", style="green", width=12)
    table.add_column("Author", style="blue", width=20)
    table.add_column("Exception Types", style="magenta")
    
    for pack in packs:
        name = pack['name']
        version = pack['version']
        author = pack['author']
        targets = ', '.join(pack.get('targets', []))
        
        table.add_row(name, version, author, targets)
    
    console.print(table)


def _display_detailed_list(console: Console, packs: list):
    """Display detailed list of packs."""
    panels = []
    
    for pack in packs:
        # Create detailed panel for each pack
        content = []
        
        # Basic info
        info_text = Text()
        info_text.append("📦 ", style="bold yellow")
        info_text.append(pack['name'], style="bold white")
        info_text.append(f" v{pack['version']}", style="green")
        content.append(info_text)
        
        # Description
        if pack.get('description'):
            desc_text = Text()
            desc_text.append("📝 ", style="blue")
            desc_text.append(pack['description'], style="white")
            content.append(desc_text)
        
        # Author
        author_text = Text()
        author_text.append("👤 ", style="cyan")
        author_text.append("Author: ", style="bold cyan")
        author_text.append(pack['author'], style="white")
        content.append(author_text)
        
        # Exception types
        if pack.get('targets'):
            targets_text = Text()
            targets_text.append("🎯 ", style="magenta")
            targets_text.append("Handles: ", style="bold magenta")
            targets_text.append(', '.join(pack['targets']), style="white")
            content.append(targets_text)
        
        # File path
        path_text = Text()
        path_text.append("📁 ", style="dim cyan")
        path_text.append("File: ", style="dim cyan")
        path_text.append(pack.get('file_path', 'Unknown'), style="dim white")
        content.append(path_text)
        
        # Create panel
        panel_content = Text('\n').join(content)
        panel = Panel(
            panel_content,
            border_style="dim white",
            padding=(1, 2)
        )
        
        panels.append(panel)
    
    # Display panels
    for panel in panels:
        console.print(panel)
        console.print()


def _display_list_summary(console: Console, packs: list):
    """Display summary statistics."""
    if not packs:
        return
    
    # Collect statistics
    total_packs = len(packs)
    exception_types = set()
    authors = set()
    
    for pack in packs:
        exception_types.update(pack.get('targets', []))
        authors.add(pack['author'])
    
    # Create summary
    summary_text = Text()
    summary_text.append("📊 ", style="bold cyan")
    summary_text.append("Summary: ", style="bold white")
    summary_text.append(f"{total_packs} packs", style="yellow")
    summary_text.append(f" • {len(exception_types)} exception types", style="green")
    summary_text.append(f" • {len(authors)} authors", style="blue")
    
    console.print(summary_text)
    
    # Show covered exception types
    if exception_types:
        types_text = Text()
        types_text.append("🎯 ", style="magenta")
        types_text.append("Exception types covered: ", style="bold magenta")
        types_text.append(', '.join(sorted(exception_types)), style="white")
        console.print(types_text)
    
    console.print()