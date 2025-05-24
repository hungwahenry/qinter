"""
qinter/utils/validation.py
"""

import re
from typing import Any, Dict, List


def is_valid_package_name(name: str) -> bool:
    """Check if a package name is valid."""
    if not isinstance(name, str):
        return False
    
    # Package name should be alphanumeric with hyphens/underscores
    pattern = r'^[a-zA-Z][a-zA-Z0-9_-]*$'
    return bool(re.match(pattern, name)) and len(name) <= 50


def validate_explanation_data(data: Dict[str, Any]) -> List[str]:
    """Validate explanation data structure."""
    errors = []
    
    required_fields = ['title', 'explanation']
    for field in required_fields:
        if field not in data:
            errors.append(f"Missing required field: {field}")
        elif not isinstance(data[field], str):
            errors.append(f"Field '{field}' must be a string")
    
    optional_fields = {
        'suggestions': list,
        'examples': list,
        'tags': list,
    }
    
    for field, expected_type in optional_fields.items():
        if field in data and not isinstance(data[field], expected_type):
            errors.append(f"Field '{field}' must be a {expected_type.__name__}")
    
    return errors