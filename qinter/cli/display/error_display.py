"""
qinter/cli/display/error_display.py
Error display coordination for Qinter.

This module coordinates between the explanation system and rich formatting.
"""

from typing import Any, Dict, Optional
from qinter.cli.display.rich_formatter import get_formatter


class ErrorDisplay:
    """Coordinates error explanation display."""
    
    def __init__(self):
        self.formatter = get_formatter()
    
    def display_explanation(self, explanation: Dict[str, Any], context: Dict[str, Any]) -> None:
        """Display a formatted error explanation."""
        if explanation:
            self.formatter.format_explanation(explanation, context)
        else:
            self._display_fallback(context)
    
    def _display_fallback(self, context: Dict[str, Any]) -> None:
        """Display a basic message when no explanation is available."""
        fallback_explanation = {
            "title": "No Explanation Available",
            "explanation": f"Qinter couldn't find a specific explanation for this {context.get('exception_type', 'error')}."
        }
        
        self.formatter.format_explanation(fallback_explanation, context)
    
    def display_activation_message(self, active: bool) -> None:
        """Display activation/deactivation message."""
        self.formatter.format_activation_message(active)
    
    def display_status(self, status: str) -> None:
        """Display current status."""
        self.formatter.format_status(status)


# Global display instance
_display = ErrorDisplay()

def get_display() -> ErrorDisplay:
    """Get the global error display instance."""
    return _display