"""
qinter/cli/commands/info.py
Info command for Qinter CLI.

Shows detailed information about explanation packs.
"""

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.columns import Columns
from qinter.packages.manager import get_package_manager


@click.command()
@click.argument('pack_name', required=True)
def info(pack_name: str):
    """
    Show detailed information about an explanation pack.
    
    Examples:
        qinter info requests
        qinter info pandas-errors
    """
    console = Console()
    manager = get_package_manager()
    
    # Get pack information
    pack_info = manager.get_pack_info(pack_name)
    
    if not pack_info:
        _display_pack_not_found(console, pack_name)
        return
    
    # Display detailed information
    _display_pack_info(console, pack_info)


def _display_pack_not_found(console: Console, pack_name: str):
    """Display message when pack is not found."""
    message = Text.assemble(
        ("📦 ", "bold yellow"),
        (f"Pack '{pack_name}' not found\n\n", "bold white"),
        ("The pack might not exist or isn't available in the registry.\n\n", "white"),
        ("Try:\n", "white"),
        ("• Check the spelling: ", "cyan"),
        ("qinter search <similar-name>\n", "cyan"),
        ("• Browse available packs: ", "cyan"),
        ("qinter search \"\"", "cyan")
    )
    
    panel = Panel(
        message,
        title="[bold white]Pack Not Found",
        border_style="red",
        padding=(1, 2)
    )
    
    console.print(panel)


def _display_pack_info(console: Console, pack_info: dict):
    """Display detailed pack information."""
    
    # Header with pack name and status
    _display_pack_header(console, pack_info)
    
    # Main information panel
    _display_main_info(console, pack_info)
    
    # Technical details
    _display_technical_info(console, pack_info)
    
    # Installation instructions
    _display_installation_info(console, pack_info)


def _display_pack_header(console: Console, pack_info: dict):
    """Display pack header with name and status."""
    name = pack_info['name']
    version = pack_info['version']
    status = pack_info.get('status', 'available')
    
    header_text = Text()
    header_text.append("📦 ", style="bold yellow")
    header_text.append(name, style="bold white")
    header_text.append(f" v{version}", style="green")
    
    if status == 'installed':
        status_text = Text("✅ Installed", style="bold green")
    else:
        status_text = Text("📥 Available", style="bold blue")
    
    # Create columns for name and status
    columns = Columns([header_text, status_text], align="left", expand=True)
    
    panel = Panel(
        columns,
        border_style="cyan",
        padding=(1, 2)
    )
    
    console.print(panel)
    console.print()


def _display_main_info(console: Console, pack_info: dict):
    """Display main pack information."""
    
    content = []
    
    # Description
    if pack_info.get('description'):
        desc_text = Text()
        desc_text.append("📝 ", style="blue")
        desc_text.append("Description\n", style="bold blue")
        desc_text.append(pack_info['description'], style="white")
        content.append(desc_text)
    
    # Author
    if pack_info.get('author'):
        author_text = Text()
        author_text.append("👤 ", style="cyan")
        author_text.append("Author: ", style="bold cyan")
        author_text.append(pack_info['author'], style="white")
        content.append(author_text)
    
    # License
    if pack_info.get('license'):
        license_text = Text()
        license_text.append("⚖️ ", style="green")
        license_text.append("License: ", style="bold green")
        license_text.append(pack_info['license'], style="white")
        content.append(license_text)
    
    # Exception types handled
    if pack_info.get('targets'):
        targets_text = Text()
        targets_text.append("🎯 ", style="magenta")
        targets_text.append("Exception Types: ", style="bold magenta")
        targets_text.append(', '.join(pack_info['targets']), style="white")
        content.append(targets_text)
    
    # Tags
    if pack_info.get('tags'):
        tags_text = Text()
        tags_text.append("🏷️ ", style="yellow")
        tags_text.append("Tags: ", style="bold yellow")
        tags_text.append(', '.join(pack_info['tags']), style="white")
        content.append(tags_text)
    
    if content:
        panel_content = Text('\n\n').join(content)
        panel = Panel(
            panel_content,
            title="[bold white]📋 Package Information",
            border_style="blue",
            padding=(1, 2)
        )
        console.print(panel)
        console.print()


def _display_technical_info(console: Console, pack_info: dict):
    """Display technical information in a table."""
    
    table = Table(
        title="🔧 Technical Details",
        show_header=True,
        header_style="bold cyan",
        border_style="dim white",
        width=80
    )
    
    table.add_column("Property", style="cyan", width=20)
    table.add_column("Value", style="white")
    
    # Add technical details
    details = [
        ("Version", pack_info.get('version', 'Unknown')),
        ("Qinter Version", pack_info.get('qinter_version', 'Unknown')),
        ("File Size", pack_info.get('file_size', 'Unknown')),
        ("Last Updated", pack_info.get('last_updated', 'Unknown')),
    ]
    
    # Add registry-specific info
    if pack_info.get('downloads'):
        details.append(("Downloads", f"{pack_info['downloads']:,}"))
    
    if pack_info.get('rating'):
        details.append(("Rating", f"⭐ {pack_info['rating']}/5.0"))
    
    # Add dependencies
    if pack_info.get('dependencies'):
        deps = ', '.join(pack_info['dependencies'])
        details.append(("Dependencies", deps))
    
    # Add links
    if pack_info.get('homepage'):
        details.append(("Homepage", pack_info['homepage']))
    
    if pack_info.get('repository'):
        details.append(("Repository", pack_info['repository']))
    
    for prop, value in details:
        table.add_row(prop, str(value))
    
    console.print(table)
    console.print()


def _display_installation_info(console: Console, pack_info: dict):
    """Display installation instructions."""
    
    name = pack_info['name']
    status = pack_info.get('status', 'available')
    
    if status == 'installed':
        # Already installed - show update/remove options
        content = Text.assemble(
            ("✅ ", "bold green"),
            ("This pack is already installed.\n\n", "bold white"),
            ("Available actions:\n", "white"),
            ("• Update to latest: ", "cyan"),
            (f"qinter update {name}\n", "bold cyan"),
            ("• Reinstall: ", "cyan"),
            (f"qinter install {name} --force\n", "bold cyan"),
            ("• Remove: ", "red"),
            (f"qinter uninstall {name}", "bold red")
        )
        border_style = "green"
        title = "🔄 Pack Management"
    else:
        # Not installed - show installation options
        content = Text.assemble(
            ("📥 ", "bold blue"),
            ("Ready to install this pack.\n\n", "bold white"),
            ("Installation command:\n", "white"),
            (f"qinter install {name}\n\n", "bold cyan"),
            ("Advanced options:\n", "white"),
            ("• Specific version: ", "cyan"),
            (f"qinter install {name} --version 1.0.0\n", "dim cyan"),
            ("• Force reinstall: ", "cyan"),
            (f"qinter install {name} --force", "dim cyan")
        )
        border_style = "blue"
        title = "📦 Installation"
    
    panel = Panel(
        content,
        title=f"[bold white]{title}",
        border_style=border_style,
        padding=(1, 2)
   )
    console.print(panel)