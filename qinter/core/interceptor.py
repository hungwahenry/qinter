"""
qinter/core/interceptor.py
Core exception interception system for Qinter.

This module handles the low-level exception hooking and context capture.
"""

import sys
import traceback
from typing import Any, Callable, Dict, List, Optional, Tuple, Type
from types import TracebackType


class ExceptionInterceptor:
    """Handles Python exception interception and context capture."""
    
    def __init__(self) -> None:
        self._original_excepthook: Optional[Callable] = None
        self._is_active: bool = False
        self._explanation_handler: Optional[Callable] = None
        
    def activate(self, explanation_handler: Optional[Callable] = None) -> None:
        """Activate the exception interceptor."""
        if self._is_active:
            return
            
        # Store original exception hook
        self._original_excepthook = sys.excepthook
        self._explanation_handler = explanation_handler
        
        # Install our custom exception hook
        sys.excepthook = self._custom_excepthook
        self._is_active = True
        
    def deactivate(self) -> None:
        """Deactivate the exception interceptor and restore original behavior."""
        if not self._is_active:
            return
            
        # Restore original exception hook
        if self._original_excepthook:
            sys.excepthook = self._original_excepthook
            
        self._is_active = False
        self._explanation_handler = None
        
    def _custom_excepthook(
        self, 
        exc_type: Type[BaseException], 
        exc_value: BaseException, 
        exc_traceback: Optional[TracebackType]
    ) -> None:
        """Custom exception hook that captures context and explains errors."""
        
        # Capture error context
        context = self._capture_context(exc_type, exc_value, exc_traceback)
        
        # Try to get explanation
        explanation = None
        if self._explanation_handler:
            try:
                explanation = self._explanation_handler(exc_value, context)
            except Exception:
                # If explanation fails, fall back to original behavior
                pass
        
        # Display explanation or fall back to original
        if explanation:
            self._display_explanation(explanation, context)
        else:
            # Fall back to original exception display
            if self._original_excepthook:
                self._original_excepthook(exc_type, exc_value, exc_traceback)
                
    def _capture_context(
        self, 
        exc_type: Type[BaseException], 
        exc_value: BaseException, 
        exc_traceback: Optional[TracebackType]
    ) -> Dict[str, Any]:
        """Capture relevant context about the error."""
        
        context = {
            "exception_type": exc_type.__name__,
            "exception_message": str(exc_value),
            "exception_args": getattr(exc_value, 'args', ()),
            "traceback_info": [],
            "local_variables": {},
            "file_context": {},
        }
        
        if exc_traceback:
            # Extract traceback information
            tb_list = traceback.extract_tb(exc_traceback)
            context["traceback_info"] = [
                {
                    "filename": frame.filename,
                    "line_number": frame.lineno,
                    "function_name": frame.name,
                    "code_line": frame.line,
                }
                for frame in tb_list
            ]
            
            # Get local variables from the last frame
            if exc_traceback.tb_frame:
                try:
                    context["local_variables"] = dict(exc_traceback.tb_frame.f_locals)
                except:
                    # Sometimes frame locals can't be accessed
                    context["local_variables"] = {}
                    
            # Get file context around error line
            if tb_list:
                last_frame = tb_list[-1]
                context["file_context"] = self._get_file_context(
                    last_frame.filename, 
                    last_frame.lineno
                )
        
        return context
    
    def _get_file_context(self, filename: str, line_number: int) -> Dict[str, Any]:
        """Get surrounding lines of code from the file where error occurred."""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            # Get 3 lines before and after the error line
            start = max(0, line_number - 4)
            end = min(len(lines), line_number + 3)
            
            return {
                "filename": filename,
                "error_line": line_number,
                "lines": [
                    {
                        "number": i + 1,
                        "content": lines[i].rstrip(),
                        "is_error_line": i + 1 == line_number
                    }
                    for i in range(start, end)
                ]
            }
        except (IOError, OSError, UnicodeDecodeError):
            return {"filename": filename, "error_line": line_number, "lines": []}
    
    def _display_explanation(self, explanation: Dict[str, Any], context: Dict[str, Any]) -> None:
        """Display the error explanation using Rich formatting."""
        try:
            from qinter.cli.display.error_display import get_display
            display = get_display()
            display.display_explanation(explanation, context)
        except ImportError:
            # Fallback to basic display if Rich isn't available
            self._display_explanation_basic(explanation, context)

    def _display_explanation_basic(self, explanation: Dict[str, Any], context: Dict[str, Any]) -> None:
        """Basic fallback display method (original implementation)."""
        print("\n" + "="*60)
        print("🔍 QINTER ERROR EXPLANATION") 
        print("="*60)
        
        if "title" in explanation:
            print(f"\n📋 {explanation['title']}")
            
        if "explanation" in explanation:
            print(f"\n💡 What happened:")
            print(f"   {explanation['explanation']}")
            
        if "suggestions" in explanation:
            print(f"\n🔧 How to fix it:")
            for i, suggestion in enumerate(explanation['suggestions'], 1):
                print(f"   {i}. {suggestion}")
                
        if "examples" in explanation:
            print(f"\n📝 Example:")
            for example in explanation['examples'][:1]:
                if isinstance(example, dict) and "code" in example:
                    print(f"   {example['code']}")
                else:
                    print(f"   {example}")
        
        print(f"\n📍 Original error:")
        print(f"   {context['exception_type']}: {context['exception_message']}")
        
        if context.get('file_context', {}).get('lines'):
            print(f"\n📄 Code context:")
            for line_info in context['file_context']['lines']:
                marker = ">>>" if line_info['is_error_line'] else "   "
                print(f"   {marker} {line_info['number']:3d}: {line_info['content']}")
        
        print("="*60 + "\n")


# Global instance
_interceptor = ExceptionInterceptor()

def activate(explanation_handler: Optional[Callable] = None) -> None:
    """Activate Qinter exception interception."""
    _interceptor.activate(explanation_handler)

def deactivate() -> None:
    """Deactivate Qinter exception interception."""
    _interceptor.deactivate()

def is_active() -> bool:
    """Check if Qinter is currently active."""
    return _interceptor._is_active