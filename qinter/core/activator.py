"""
qinter/core/activator.py

Provides the simple interface for users to activate/deactivate Qinter.
"""

from typing import Optional
from qinter.core.interceptor import activate as _activate, deactivate as _deactivate, is_active


def activate() -> None:
    """
    Activate Qinter error explanations.
    
    This will intercept Python exceptions and provide human-readable
    explanations when errors occur.
    
    Example:
        >>> import qinter
        >>> qinter.activate()
        >>> name_that_doesnt_exist  # Will show beautiful explanation
    """
    def lazy_explain_error(exception, context):
        # Import here to avoid circular import
        try:
            from qinter.explanations.engine import explain_error
            return explain_error(exception, context)
        except ImportError:
            return None
    
    _activate(explanation_handler=lazy_explain_error)
    
    # Use rich formatting for activation message
    try:
        from qinter.cli.display.error_display import get_display
        get_display().display_activation_message(True)
    except ImportError:
        print("🔍 Qinter activated! Errors will now show beautiful explanations.")


def deactivate() -> None:
    """
    Deactivate Qinter and return to standard Python error behavior.
    
    Example:
        >>> qinter.deactivate()
        >>> name_that_doesnt_exist  # Will show standard Python error
    """
    _deactivate()
    
    # Use rich formatting for deactivation message
    try:
        from qinter.cli.display.error_display import get_display
        get_display().display_activation_message(False)
    except ImportError:
        print("🔍 Qinter deactivated. Back to standard Python errors.")


def status() -> str:
    """
    Get current Qinter activation status.
    
    Returns:
        str: "active" or "inactive"
    """
    return "active" if is_active() else "inactive"