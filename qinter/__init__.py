"""
qinter/__init__.py

Qinter provides intelligent, human-readable explanations for Python errors
and a package management system for extensible error explanation packs.

Usage:
    import qinter
    qinter.activate()
    
    # Your code here - errors will now show beautiful explanations!
"""

from qinter.__version__ import __version__
from qinter.core.activator import activate, deactivate, status

__all__ = ["__version__", "activate", "deactivate", "status"]