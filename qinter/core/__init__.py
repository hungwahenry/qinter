"""
qinter/core/__init__.py
"""

from qinter.core.activator import activate, deactivate, status
from qinter.core.interceptor import is_active

__all__ = ["activate", "deactivate", "status", "is_active"]