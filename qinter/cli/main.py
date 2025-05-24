"""
qinter/cli/main.py
Main CLI entry point for Qinter.

This module provides the command-line interface for managing
explanation packs and configuring Qinter.
"""

import click
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from qinter.__version__ import __version__
from qinter.cli.commands.install import install
from qinter.cli.commands.list import list_packs
from qinter.cli.commands.search import search
from qinter.cli.commands.info import info


@click.group()
@click.version_option(version=__version__, prog_name="Qinter")
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.pass_context
def cli(ctx, verbose):
    """
    🔍 Qinter - Human-readable Python error explanations
    
    Qinter transforms cryptic Python errors into clear, actionable explanations
    with suggested fixes and examples.
    """
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose


@cli.command()
def activate():
    """Activate Qinter error explanations for the current session."""
    try:
        import qinter
        qinter.activate()
    except Exception as e:
        console = Console()
        console.print(f"❌ Failed to activate Qinter: {e}")


@cli.command()
def deactivate():
    """Deactivate Qinter error explanations."""
    try:
        import qinter
        qinter.deactivate()
    except Exception as e:
        console = Console()
        console.print(f"❌ Failed to deactivate Qinter: {e}")


@cli.command()
def status():
    """Show current Qinter status and statistics."""
    console = Console()
    
    try:
        import qinter
        from qinter.explanations.engine import get_engine
        from qinter.packages.manager import get_package_manager
        
        # Get current status
        current_status = qinter.status()
        
        # Get engine statistics
        engine = get_engine()
        engine_stats = engine.get_statistics()
        
        # Get installed packs
        manager = get_package_manager()
        installed_packs = manager.list_installed_packs()
        
        _display_status_panel(console, current_status, engine_stats, installed_packs)
        
    except Exception as e:
        console.print(f"❌ Failed to get status: {e}")


@cli.command()
@click.argument('pack_names', nargs=-1, required=True)
def uninstall(pack_names):
    """
    Uninstall explanation packs.
    
    Examples:
        qinter uninstall requests
        qinter uninstall pandas numpy
    """
    console = Console()
    
    try:
        from qinter.packages.manager import get_package_manager
        manager = get_package_manager()
        
        _display_uninstall_header(console, pack_names)
        
        results = {}
        for pack_name in pack_names:
            success = manager.uninstall_pack(pack_name)
            results[pack_name] = 'success' if success else 'failed'
        
        _display_uninstall_results(console, results)
        
    except Exception as e:
        console.print(f"❌ Uninstall failed: {e}")


@cli.command()
@click.argument('pack_names', nargs=-1)
def update(pack_names):
    """
    Update explanation packs to latest versions.
    
    Examples:
        qinter update              # Update all packs
        qinter update requests     # Update specific pack
        qinter update pandas numpy # Update multiple packs
    """
    console = Console()
    
    try:
        from qinter.packages.manager import get_package_manager
        manager = get_package_manager()
        
        if not pack_names:
            # Update all packs
            console.print("🔄 Updating all installed packs...")
            results = manager.update_all_packs()
        else:
            # Update specific packs
            _display_update_header(console, pack_names)
            results = {}
            for pack_name in pack_names:
                success = manager.update_pack(pack_name)
                results[pack_name] = success
        
        _display_update_results(console, results)
        
    except Exception as e:
        console.print(f"❌ Update failed: {e}")


@cli.command()
def config():
    """Show and manage Qinter configuration."""
    console = Console()
    
    try:
        from qinter.config.settings import get_settings
        settings = get_settings()
        
        _display_config_panel(console, settings)
        
    except Exception as e:
        console.print(f"❌ Failed to show config: {e}")


@cli.command()
def doctor():
    """Run diagnostics to check Qinter installation and configuration."""
    console = Console()
    
    console.print("🏥 Running Qinter diagnostics...\n")
    
    # Check installation
    _check_installation(console)
    
    # Check core packs
    _check_core_packs(console)
    
    # Check configuration
    _check_configuration(console)
    
    # Check explanation engine
    _check_explanation_engine(console)
    
    console.print("\n✅ Diagnostics completed!")


# Add subcommands
cli.add_command(install)
cli.add_command(list_packs, name='list')
cli.add_command(search)
cli.add_command(info)


def _display_status_panel(console: Console, status: str, stats: dict, packs: list):
    """Display comprehensive status information."""
    
    # Main status
    if status == "active":
        status_text = Text("🟢 ACTIVE", style="bold green")
    else:
        status_text = Text("🔴 INACTIVE", style="bold red")
    
    # Create status content
    content = []
    
    # Status line
    status_line = Text()
    status_line.append("🔍 Qinter Status: ", style="bold white")
    status_line.append(status_text)
    content.append(status_line)
    
    # Engine statistics
    engine_line = Text()
    engine_line.append(f"📊 Engine: ", style="bold cyan")
    engine_line.append(f"{stats['total_explanations']} explanations loaded from {stats['loaded_packs']} packs", style="white")
    content.append(engine_line)
    
    # Exception types covered
    if stats['exception_types_covered']:
        types_line = Text()
        types_line.append("🎯 Coverage: ", style="bold magenta")
        types_line.append(', '.join(stats['exception_types_covered']), style="white")
        content.append(types_line)
    
    # Installed packs
    packs_line = Text()
    packs_line.append(f"📦 Installed Packs: ", style="bold yellow")
    packs_line.append(f"{len(packs)} total", style="white")
    content.append(packs_line)
    
    # Validation errors
    if stats['validation_errors']:
        error_line = Text()
        error_line.append("⚠️ Issues: ", style="bold red")
        error_line.append(f"{len(stats['validation_errors'])} validation errors", style="red")
        content.append(error_line)
    
    panel_content = Text('\n').join(content)
    
    panel = Panel(
        panel_content,
        title="[bold white]🔍 Qinter Status Dashboard",
        border_style="cyan",
        padding=(1, 2)
    )
    
    console.print(panel)


def _display_uninstall_header(console: Console, pack_names):
    """Display uninstall header."""
    header_text = Text()
    header_text.append("🗑️ ", style="bold red")
    header_text.append("Uninstalling Explanation Packs", style="bold white")
    
    pack_list = ", ".join(pack_names)
    subtitle = Text()
    subtitle.append("Packs: ", style="bold white")
    subtitle.append(pack_list, style="yellow")
    
    panel = Panel(
        Text.assemble(header_text, "\n", subtitle),
        border_style="red",
        padding=(1, 2)
    )
    
    console.print(panel)
    console.print()


def _display_uninstall_results(console: Console, results: dict):
    """Display uninstall results."""
    for pack_name, result in results.items():
        if result == 'success':
            console.print(f"✅ Successfully uninstalled {pack_name}")
        else:
            console.print(f"❌ Failed to uninstall {pack_name}")
    
    console.print()


def _display_update_header(console: Console, pack_names):
    """Display update header."""
    header_text = Text()
    header_text.append("🔄 ", style="bold blue")
    header_text.append("Updating Explanation Packs", style="bold white")
    
    pack_list = ", ".join(pack_names)
    subtitle = Text()
    subtitle.append("Packs: ", style="bold white")
    subtitle.append(pack_list, style="yellow")
    
    panel = Panel(
        Text.assemble(header_text, "\n", subtitle),
        border_style="blue",
        padding=(1, 2)
    )
    
    console.print(panel)
    console.print()


def _display_update_results(console: Console, results: dict):
    """Display update results."""
    for pack_name, result in results.items():
        if result:
            console.print(f"✅ Successfully updated {pack_name}")
        else:
            console.print(f"❌ Failed to update {pack_name}")
    
    console.print()


def _display_config_panel(console: Console, settings):
    """Display configuration information."""
    
    content = []
    
    # General settings
    general_text = Text()
    general_text.append("⚙️ General Settings\n", style="bold cyan")
    general_text.append(f"  Auto Update: {settings.auto_update}\n", style="white")
    general_text.append(f"  Cache Duration: {settings.cache_duration_days} days\n", style="white")
    general_text.append(f"  Debug Mode: {settings.debug_mode}\n", style="white")
    content.append(general_text)
    
    # Display settings
    display_text = Text()
    display_text.append("🎨 Display Settings\n", style="bold green")
    display_text.append(f"  Max Suggestions: {settings.max_suggestions}\n", style="white")
    display_text.append(f"  Max Examples: {settings.max_examples}\n", style="white")
    display_text.append(f"  Color Theme: {settings.color_theme}\n", style="white")
    content.append(display_text)
    
    # Registries
    registry_text = Text()
    registry_text.append("📡 Registries\n", style="bold magenta")
    for registry in settings.registries:
        status = "✅" if registry.enabled else "❌"
        registry_text.append(f"  {status} {registry.name} (priority: {registry.priority})\n", style="white")
    content.append(registry_text)
    
    panel_content = Text('\n').join(content)
    
    panel = Panel(
        panel_content,
        title="[bold white]⚙️ Qinter Configuration",
        border_style="cyan",
        padding=(1, 2)
    )
    
    console.print(panel)


def _check_installation(console: Console):
    """Check Qinter installation."""
    console.print("🔍 Checking installation...")
    
    try:
        import qinter
        console.print(f"  ✅ Qinter {qinter.__version__} installed correctly")
    except Exception as e:
        console.print(f"  ❌ Installation issue: {e}")
        return
    
    # Check dependencies
    try:
        import rich
        import yaml
        import click
        console.print("  ✅ All dependencies available")
    except ImportError as e:
        console.print(f"  ❌ Missing dependency: {e}")


def _check_core_packs(console: Console):
    """Check core explanation packs."""
    console.print("\n📦 Checking core explanation packs...")
    
    try:
        from qinter.packages.loader import get_loader
        loader = get_loader()
        core_packs = loader.load_core_packs()
        
        if core_packs:
            console.print(f"  ✅ {len(core_packs)} core packs loaded successfully")
            for pack in core_packs:
                console.print(f"    • {pack.metadata.name} v{pack.metadata.version}")
        else:
            console.print("  ⚠️ No core packs found")
            
        errors = loader.get_validation_errors()
        if errors:
            console.print(f"  ⚠️ {len(errors)} validation errors found")
            
    except Exception as e:
        console.print(f"  ❌ Core pack check failed: {e}")


def _check_configuration(console: Console):
    """Check configuration."""
    console.print("\n⚙️ Checking configuration...")
    
    try:
        from qinter.config.settings import get_settings
        settings = get_settings()
        console.print(f"  ✅ Configuration loaded successfully")
        console.print(f"    • {len(settings.registries)} registries configured")
    except Exception as e:
        console.print(f"  ❌ Configuration issue: {e}")


def _check_explanation_engine(console: Console):
    """Check explanation engine."""
    console.print("\n🧠 Checking explanation engine...")
    
    try:
        from qinter.explanations.engine import get_engine
        engine = get_engine()
        stats = engine.get_statistics()
        
        console.print(f"  ✅ Engine operational")
        console.print(f"    • {stats['total_explanations']} explanations loaded")
        console.print(f"    • {len(stats['exception_types_covered'])} exception types covered")
        
    except Exception as e:
        console.print(f"  ❌ Engine issue: {e}")


def main():
    """Main entry point for the CLI."""
    cli()


if __name__ == '__main__':
    main()