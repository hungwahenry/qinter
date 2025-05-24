"""
qinter/cli/display/rich_formatter.py
Enhanced Rich terminal formatting for stunning error displays.

This module provides gorgeous, sophisticated formatting with tabs, custom borders,
themes, and dynamic visual elements.
"""

from typing import Any, Dict, List, Optional
from rich.console import Console, Group
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text
from rich.columns import Columns
from rich.rule import Rule
from rich.tree import Tree
from rich.align import Align
from rich.padding import Padding
from rich.layout import Layout
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.emoji import Emoji
from rich import box
import time


class QinterRichFormatter:
    """Enhanced formatter with stunning visual design."""
    
    def __init__(self):
        self.console = Console(width=120)  # Wider console for better layout
        
        # Custom box styles for different types of content
        self.main_box = box.DOUBLE_EDGE
        self.code_box = box.HEAVY
        self.suggestion_box = box.ROUNDED
        self.example_box = box.ASCII2
        
        # Color scheme
        self.colors = {
            'primary': '#FF6B6B',      # Coral red
            'secondary': '#4ECDC4',    # Teal
            'accent': '#45B7D1',       # Blue
            'success': '#96CEB4',      # Mint green
            'warning': '#FFEAA7',      # Light yellow
            'info': '#DDA0DD',         # Plum
            'code': '#2D3748',         # Dark gray
            'text': '#E2E8F0',         # Light gray
        }
    
    def format_explanation(self, explanation: Dict[str, Any], context: Dict[str, Any]) -> None:
        """Format and display a complete error explanation with stunning visuals."""
        
        # Create dramatic entrance effect
        self._show_entrance_animation()
        
        # Create main layout with tabs
        layout = Layout()
        
        # Split into header and main content
        layout.split_column(
            Layout(name="header", size=7),
            Layout(name="main")
        )
        
        # Create header with title and metadata
        header_content = self._create_header(explanation, context)
        layout["header"].update(Panel(
            header_content,
            box=self.main_box,
            style=f"bold {self.colors['primary']}",
            border_style=self.colors['accent']
        ))
        
        # Create tabbed interface for main content
        tabs = self._create_tabbed_interface(explanation, context)
        layout["main"].update(tabs)
        
        # Display the complete layout
        self.console.print(layout)
        
        # Add some visual flair at the end
        self._show_completion_effect()
    
    def _show_entrance_animation(self) -> None:
        """Show a brief animation when displaying error."""
        with Progress(
            SpinnerColumn(spinner_style=self.colors['accent']),
            TextColumn("[bold cyan]Analyzing error..."),
            console=self.console,
            transient=True
        ) as progress:
            task = progress.add_task("", total=100)
            for i in range(100):
                progress.update(task, advance=1)
                time.sleep(0.01)  # Very brief animation
        
        # Clear and add spacing
        self.console.print()
    
    def _create_header(self, explanation: Dict[str, Any], context: Dict[str, Any]) -> Group:
        """Create a stunning header with title and metadata."""
        
        # Main title with dramatic styling
        title = Text()
        title.append("⚡ ", style=f"bold {self.colors['warning']}")
        title.append("QINTER", style=f"bold {self.colors['primary']} underline")
        title.append(" ERROR ANALYSIS", style=f"bold {self.colors['secondary']}")
        
        # Subtitle with error type
        subtitle = Text()
        subtitle.append("🔍 ", style=f"bold {self.colors['info']}")
        subtitle.append(explanation.get('title', 'Error Detected'), style=f"bold {self.colors['accent']}")
        
        # Metadata row
        error_type = context.get('exception_type', 'Unknown')
        metadata = Text()
        metadata.append("📊 Type: ", style="bold cyan")
        metadata.append(error_type, style=f"bold {self.colors['warning']}")
        metadata.append("  📁 File: ", style="bold cyan")
        
        file_context = context.get('file_context', {})
        if file_context.get('filename'):
            filename = file_context['filename'].split('/')[-1]  # Just filename
            metadata.append(filename, style=f"bold {self.colors['success']}")
            if file_context.get('error_line'):
                metadata.append(f":{file_context['error_line']}", style=f"bold {self.colors['info']}")
        else:
            metadata.append("interactive", style=f"bold {self.colors['info']}")
        
        return Group(
            Align.center(title),
            Align.center(subtitle),
            Align.center(metadata)
        )
    
    def _create_tabbed_interface(self, explanation: Dict[str, Any], context: Dict[str, Any]) -> Panel:
        """Create a tabbed interface for different content sections."""
        
        # Create tabs
        tabs_table = Table.grid(expand=True)
        tabs_table.add_column(style="bold cyan", ratio=1)
        tabs_table.add_column(style="bold green", ratio=1)
        tabs_table.add_column(style="bold yellow", ratio=1)
        tabs_table.add_column(style="bold magenta", ratio=1)
        
        # Tab headers
        tab1 = Text("📋 EXPLANATION", style="bold cyan")
        tab2 = Text("💡 SOLUTIONS", style="bold green") 
        tab3 = Text("📝 EXAMPLES", style="bold yellow")
        tab4 = Text("🔍 CONTEXT", style="bold magenta")
        
        tabs_table.add_row(
            Align.center(tab1),
            Align.center(tab2), 
            Align.center(tab3),
            Align.center(tab4)
        )
        
        # Tab content
        content_panels = self._create_tab_content(explanation, context)
        
        # Combine tabs and content
        main_content = Group(
            Panel(tabs_table, box=box.SIMPLE, style="dim"),
            *content_panels
        )
        
        return Panel(
            main_content,
            box=self.main_box,
            border_style=self.colors['secondary'],
            title="[bold white]🎯 Error Analysis Dashboard",
            title_align="center"
        )
    
    def _create_tab_content(self, explanation: Dict[str, Any], context: Dict[str, Any]) -> List[Panel]:
        """Create content for each tab."""
        panels = []
        
        # Tab 1: Explanation
        explanation_content = self._create_explanation_tab(explanation)
        panels.append(Panel(
            explanation_content,
            title="[cyan]📋 What Happened",
            box=self.suggestion_box,
            border_style="cyan",
            padding=(1, 2)
        ))
        
        # Tab 2: Solutions
        if explanation.get('suggestions'):
            solutions_content = self._create_solutions_tab(explanation['suggestions'])
            panels.append(Panel(
                solutions_content,
                title="[green]💡 How to Fix It",
                box=self.suggestion_box,
                border_style="green",
                padding=(1, 2)
            ))
        
        # Tab 3: Examples
        if explanation.get('examples'):
            examples_content = self._create_examples_tab(explanation['examples'])
            panels.append(Panel(
                examples_content,
                title="[yellow]📝 Code Examples",
                box=self.example_box,
                border_style="yellow",
                padding=(1, 2)
            ))
        
        # Tab 4: Context
        context_content = self._create_context_tab(context)
        panels.append(Panel(
            context_content,
            title="[magenta]🔍 Error Context",
            box=self.code_box,
            border_style="magenta",
            padding=(1, 2)
        ))
        
        return panels
    
    def _create_explanation_tab(self, explanation: Dict[str, Any]) -> Group:
        """Create the explanation tab content."""
        
        # Main explanation with beautiful formatting
        text = Text()
        text.append("🎯 ", style="bold red")
        text.append("Root Cause:\n", style="bold cyan underline")
        text.append(f"   {explanation.get('explanation', 'No explanation available')}", 
                   style="white")
        
        # Add severity indicator
        severity_table = Table.grid(expand=True)
        severity_table.add_column()
        severity_table.add_column(justify="right")
        
        severity_table.add_row(
            Text("⚠️  Severity Level:", style="bold yellow"),
            Text("MEDIUM", style="bold orange1")  # Could be dynamic based on error type
        )
        
        return Group(text, "", severity_table)
    
    def _create_solutions_tab(self, suggestions: List[str]) -> Tree:
        """Create an interactive tree of solutions."""
        
        tree = Tree("🔧 [bold green]Recommended Solutions")
        
        for i, suggestion in enumerate(suggestions, 1):
            # Create styled branches
            priority = "🔥 HIGH" if i <= 2 else "📌 MEDIUM"
            branch = tree.add(f"[bold yellow]{priority}[/] Solution {i}")
            branch.add(Text(suggestion, style="white"))
            
            # Add difficulty indicator
            difficulty = "⭐ Easy" if i == 1 else "⭐⭐ Medium" if i <= 3 else "⭐⭐⭐ Advanced"
            branch.add(Text(f"Difficulty: {difficulty}", style="dim cyan"))
        
        return tree
    
    def _create_examples_tab(self, examples: List[Any]) -> Group:
        """Create beautiful code examples with syntax highlighting."""
        
        example_panels = []
        
        for i, example in enumerate(examples, 1):
            if isinstance(example, dict):
                # Structured example
                title = example.get('description', f'Example {i}')
                code = example.get('code', str(example))
            else:
                title = f'Example {i}'
                code = str(example)
            
            # Create syntax highlighted code
            syntax = Syntax(
                code,
                "python",
                theme="github-dark",
                line_numbers=True,
                background_color="default",
                code_width=80
            )
            
            # Wrap in a mini panel
            example_panel = Panel(
                syntax,
                title=f"[bold yellow]💡 {title}",
                box=box.SIMPLE,
                border_style="yellow",
                padding=(1, 1)
            )
            
            example_panels.append(example_panel)
        
        return Group(*example_panels)
    
    def _create_context_tab(self, context: Dict[str, Any]) -> Group:
        """Create detailed context information."""
        
        elements = []
        
        # Code context with enhanced styling
        file_context = context.get('file_context', {})
        if file_context.get('lines'):
            code_lines = []
            for line_info in file_context['lines']:
                line_num = line_info['number']
                content = line_info['content']
                is_error = line_info.get('is_error_line', False)
                
                if is_error:
                    # Highlight error line dramatically
                    code_lines.append(f"🔥 {line_num:3d}: {content}")
                else:
                    code_lines.append(f"   {line_num:3d}: {content}")
            
            code_text = "\n".join(code_lines)
            syntax = Syntax(
                code_text,
                "python",
                theme="monokai",
                line_numbers=False,
                background_color="default"
            )
            
            elements.append(Panel(
                syntax,
                title="[bold white]📄 Source Code",
                box=box.SIMPLE,
                border_style="white"
            ))
        
        # Variables table
        local_vars = context.get('local_variables', {})
        if local_vars:
            var_table = Table(
                title="🔧 Local Variables",
                box=box.SIMPLE_HEAD,
                header_style="bold cyan"
            )
            var_table.add_column("Variable", style="yellow")
            var_table.add_column("Type", style="green")  
            var_table.add_column("Value", style="white")
            
            for name, value in list(local_vars.items())[:5]:  # Limit to 5
                if not name.startswith('_'):
                    var_table.add_row(
                        name,
                        type(value).__name__,
                        str(value)[:50] + "..." if len(str(value)) > 50 else str(value)
                    )
            
            elements.append(var_table)
        
        # Original error
        error_text = Text()
        error_text.append("💥 ", style="bold red")
        error_text.append("Original Error: ", style="bold red underline")
        error_text.append(f"{context.get('exception_type', 'Unknown')}: ", style="bold yellow")
        error_text.append(context.get('exception_message', 'No message'), style="red")
        
        elements.append(Panel(
            error_text,
            box=box.SIMPLE,
            border_style="red"
        ))
        
        return Group(*elements)
    
    def _show_completion_effect(self) -> None:
        """Show completion effect."""
        
        # Add a beautiful separator
        rule = Rule(
            Text("Analysis Complete", style=f"bold {self.colors['success']}"),
            style=self.colors['accent']
        )
        self.console.print(rule)
        
        # Add helpful tip
        tip = Text()
        tip.append("💡 ", style="bold yellow")
        tip.append("Pro Tip: ", style="bold cyan")
        tip.append("Use ", style="white")
        tip.append("qinter.deactivate()", style="bold green")
        tip.append(" to return to standard Python errors", style="white")
        
        self.console.print(Align.center(tip))
        self.console.print()
    
    def format_activation_message(self, active: bool) -> None:
        """Format dramatic activation/deactivation messages."""
        if active:
            # Activation effect
            text = Text()
            text.append("🚀 ", style="bold green")
            text.append("QINTER ACTIVATED", style="bold green underline")
            text.append(" - Beautiful error explanations enabled!", style="bold white")
            
            panel = Panel(
                Align.center(text),
                box=self.main_box,
                style="bold green",
                border_style="green"
            )
        else:
            # Deactivation effect
            text = Text()
            text.append("🛑 ", style="bold red")
            text.append("QINTER DEACTIVATED", style="bold red underline")
            text.append(" - Standard Python errors restored", style="bold white")
            
            panel = Panel(
                Align.center(text),
                box=self.main_box,
                style="bold red", 
                border_style="red"
            )
        
        self.console.print(panel)
    
    def format_status(self, status: str) -> None:
        """Format dramatic status display."""
        if status == "active":
            emoji = "🟢"
            status_text = "ACTIVE"
            color = "bold green"
        else:
            emoji = "🔴"
            status_text = "INACTIVE"
            color = "bold red"
        
        text = Text()
        text.append(f"{emoji} Qinter Status: ", style="bold white")
        text.append(status_text, style=color)
        
        panel = Panel(
            Align.center(text),
            box=box.DOUBLE,
            border_style=color.split()[1]  # Extract color
        )
        
        self.console.print(panel)


# Global formatter instance
_formatter = QinterRichFormatter()

def get_formatter() -> QinterRichFormatter:
    """Get the global Rich formatter instance."""
    return _formatter