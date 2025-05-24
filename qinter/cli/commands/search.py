"""
qinter/cli/commands/search.py
Search command for Qinter CLI.

Searches for explanation packs in the registry.
"""

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn
from qinter.packages.manager import get_package_manager


@click.command()
@click.argument('query', required=True)
@click.option('--limit', '-l', default=20, help='Maximum number of results to show')
@click.option('--sort', '-s', 
              type=click.Choice(['relevance', 'downloads', 'rating', 'name']), 
              default='relevance', help='Sort results by')
def search(query: str, limit: int, sort: str):
    """
    Search for explanation packs in the registry.
    
    Examples:
        qinter search http
        qinter search "data science" --limit 10
        qinter search pandas --sort downloads
    """
    console = Console()
    manager = get_package_manager()
    
    # Display search header
    _display_search_header(console, query)
    
    # Perform search with progress indicator
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True
    ) as progress:
        task = progress.add_task("Searching registry...", total=100)
        
        try:
            results = manager.search_packs(query)
            progress.update(task, advance=100, description="Search completed")
            
        except Exception as e:
            console.print(f"❌ Search failed: {e}")
            return
    
    if not results:
        _display_no_results_message(console, query)
        return
    
    # Sort results
    results = _sort_results(results, sort)
    
    # Limit results
    if len(results) > limit:
        results = results[:limit]
        truncated = True
    else:
        truncated = False
    
    # Display results
    _display_search_results(console, results, query, sort)
    
    if truncated:
        console.print(f"📄 Showing first {limit} results. Use --limit to see more.")
    
    # Display help message
    _display_search_help(console)


def _display_search_header(console: Console, query: str):
    """Display search header."""
    header_text = Text()
    header_text.append("🔍 ", style="bold yellow")
    header_text.append("Searching Explanation Packs", style="bold cyan")
    
    query_text = Text()
    query_text.append("Query: ", style="bold white")
    query_text.append(f'"{query}"', style="yellow")
    
    content = Text.assemble(header_text, "\n", query_text)
    
    panel = Panel(
        content,
        title="[bold white]Qinter Package Registry",
        border_style="cyan",
        padding=(1, 2)
    )
    
    console.print(panel)
    console.print()


def _display_no_results_message(console: Console, query: str):
    """Display message when no results found."""
    message = Text.assemble(
        ("🔍 ", "bold yellow"),
        (f'No packs found for "{query}"\n\n', "bold white"),
        ("Try:\n", "white"),
        ("• Using different keywords\n", "cyan"),
        ("• Searching for broader terms\n", "cyan"),
        ("• Using 'qinter list' to see available packs\n", "cyan")
    )
    
    panel = Panel(
        message,
        title="[bold white]No Results",
        border_style="yellow",
        padding=(1, 2)
    )
    
    console.print(panel)


def _display_search_results(console: Console, results: list, query: str, sort_by: str):
    """Display search results in a table."""
    table = Table(
        title=f"📋 Search Results for '{query}' (sorted by {sort_by})",
        show_header=True,
        header_style="bold cyan",
        border_style="dim white"
    )
    
    table.add_column("Pack Name", style="yellow", width=20)
    table.add_column("Version", style="green", width=10)
    table.add_column("Description", style="white", width=40)
    table.add_column("Downloads", style="blue", width=12)
    table.add_column("Rating", style="magenta", width=8)
    table.add_column("Tags", style="dim cyan")
    
    # Check which packs are already installed
    manager = get_package_manager()
    
    for pack in results:
        name = pack['name']
        version = pack['version']
        description = pack['description']
        downloads = f"{pack.get('downloads', 0):,}"
        rating = f"⭐ {pack.get('rating', 0):.1f}"
        tags = ', '.join(pack.get('tags', [])[:3])  # Show first 3 tags
        
        # Highlight if already installed
        if manager.is_pack_installed(name):
            name_display = Text()
            name_display.append(name, style="yellow")
            name_display.append(" (installed)", style="dim green")
        else:
            name_display = name
        
        table.add_row(name_display, version, description, downloads, rating, tags)
    
    console.print(table)
    console.print()


def _display_search_help(console: Console):
    """Display helpful commands after search results."""
    help_text = Text()
    help_text.append("💡 ", style="bold blue")
    help_text.append("Next steps:\n", style="bold white")
    help_text.append("• Install a pack: ", style="white")
    help_text.append("qinter install <pack-name>\n", style="cyan")
    help_text.append("• Get pack details: ", style="white")
    help_text.append("qinter info <pack-name>\n", style="cyan")
    help_text.append("• List installed: ", style="white")
    help_text.append("qinter list", style="cyan")
    
    console.print(help_text)
    console.print()


def _sort_results(results: list, sort_by: str) -> list:
    """Sort search results by the specified criteria."""
    if sort_by == 'downloads':
        return sorted(results, key=lambda x: x.get('downloads', 0), reverse=True)
    elif sort_by == 'rating':
        return sorted(results, key=lambda x: x.get('rating', 0), reverse=True)
    elif sort_by == 'name':
        return sorted(results, key=lambda x: x['name'].lower())
    else:  # relevance (default)
        return results  # Assume registry returns in relevance order