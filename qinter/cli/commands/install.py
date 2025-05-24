"""
qinter/cli/commands/install.py
Install command for Qinter CLI.

Handles installation of explanation packs from the registry.
"""

import click
from typing import List
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from qinter.packages.manager import get_package_manager
from qinter.cli.display.rich_formatter import get_formatter


@click.command()
@click.argument('pack_names', nargs=-1, required=True)
@click.option('--version', '-v', help='Specific version to install')
@click.option('--force', '-f', is_flag=True, help='Force reinstall if already installed')
@click.option('--dry-run', is_flag=True, help='Show what would be installed without installing')
def install(pack_names: List[str], version: str, force: bool, dry_run: bool):
    """
    Install explanation packs from the registry.
    
    Examples:
        qinter install requests
        qinter install pandas numpy --version latest
        qinter install django --force
    """
    console = Console()
    formatter = get_formatter()
    manager = get_package_manager()
    
    # Display header
    _display_install_header(console, pack_names, dry_run)
    
    # Process each pack
    results = {}
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    ) as progress:
        
        overall_task = progress.add_task("Installing packs...", total=len(pack_names))
        
        for pack_name in pack_names:
            pack_task = progress.add_task(f"Processing {pack_name}...", total=100)
            
            try:
                # Update progress
                progress.update(pack_task, advance=20, description=f"Checking {pack_name}...")
                
                # Check if already installed
                if manager.is_pack_installed(pack_name) and not force:
                    installed_version = manager.get_installed_version(pack_name)
                    results[pack_name] = {
                        'status': 'already_installed',
                        'version': installed_version,
                        'message': f"Already installed (v{installed_version})"
                    }
                    progress.update(pack_task, advance=80, description=f"{pack_name} already installed")
                    continue
                
                # Get pack info
                progress.update(pack_task, advance=20, description=f"Getting info for {pack_name}...")
                pack_info = manager.get_pack_info(pack_name)
                
                if not pack_info:
                    results[pack_name] = {
                        'status': 'not_found',
                        'message': 'Pack not found in registry'
                    }
                    progress.update(pack_task, advance=60, description=f"{pack_name} not found")
                    continue
                
                # Dry run - just show what would happen
                if dry_run:
                    results[pack_name] = {
                        'status': 'would_install',
                        'version': pack_info.get('version', 'unknown'),
                        'message': f"Would install v{pack_info.get('version', 'unknown')}"
                    }
                    progress.update(pack_task, advance=60, description=f"Would install {pack_name}")
                    continue
                
                # Install the pack
                progress.update(pack_task, advance=30, description=f"Installing {pack_name}...")
                
                success = manager.install_pack(pack_name, version or "latest")
                
                if success:
                    results[pack_name] = {
                        'status': 'installed',
                        'version': pack_info.get('version', 'unknown'),
                        'message': f"Successfully installed v{pack_info.get('version', 'unknown')}"
                    }
                else:
                    results[pack_name] = {
                        'status': 'failed',
                        'message': 'Installation failed'
                    }
                
                progress.update(pack_task, advance=30, description=f"Completed {pack_name}")
                
            except Exception as e:
                results[pack_name] = {
                    'status': 'error',
                    'message': f'Error: {str(e)}'
                }
                progress.update(pack_task, advance=100, description=f"Error with {pack_name}")
            
            progress.update(overall_task, advance=1)
    
    # Display results
    _display_install_results(console, results, dry_run)


def _display_install_header(console: Console, pack_names: List[str], dry_run: bool):
    """Display installation header."""
    action = "Dry Run - Installation Preview" if dry_run else "Installing Explanation Packs"
    
    header_text = Text()
    header_text.append("📦 ", style="bold yellow")
    header_text.append(action, style="bold cyan")
    
    pack_list = ", ".join(pack_names)
    subtitle = Text()
    subtitle.append("Packs: ", style="bold white")
    subtitle.append(pack_list, style="yellow")
    
    panel = Panel(
        Text.assemble(header_text, "\n", subtitle),
        title="[bold white]Qinter Package Manager",
        border_style="cyan",
        padding=(1, 2)
    )
    
    console.print(panel)
    console.print()


def _display_install_results(console: Console, results: dict, dry_run: bool):
    """Display installation results in a beautiful table."""
    
    # Create results table
    table = Table(
        title="📋 Installation Results" if not dry_run else "📋 Dry Run Results",
        show_header=True,
        header_style="bold cyan",
        border_style="dim white"
    )
    
    table.add_column("Pack Name", style="yellow", width=20)
    table.add_column("Status", style="bold", width=15)
    table.add_column("Version", style="green", width=12)
    table.add_column("Message", style="white")
    
    # Add rows
    for pack_name, result in results.items():
        status = result['status']
        version = result.get('version', 'N/A')
        message = result['message']
        
        # Style status based on result
        if status == 'installed':
            status_text = Text("✅ Installed", style="bold green")
        elif status == 'already_installed':
            status_text = Text("📦 Exists", style="bold blue")
        elif status == 'would_install':
            status_text = Text("🔄 Would Install", style="bold yellow")
        elif status == 'not_found':
            status_text = Text("❌ Not Found", style="bold red")
        elif status == 'failed':
            status_text = Text("💥 Failed", style="bold red")
        else:
            status_text = Text("⚠️ Error", style="bold magenta")
        
        table.add_row(pack_name, status_text, version, message)
    
    console.print(table)
    
    # Summary
    total = len(results)
    successful = len([r for r in results.values() if r['status'] in ['installed', 'already_installed']])
    failed = total - successful
    
    summary_text = Text()
    summary_text.append(f"📊 Summary: ", style="bold cyan")
    summary_text.append(f"{successful}/{total} successful", style="bold green")
    
    if failed > 0:
        summary_text.append(f", {failed} failed", style="bold red")
    
    console.print()
    console.print(summary_text)
    console.print()