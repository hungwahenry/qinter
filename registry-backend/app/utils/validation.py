"""
registry-backend/app/utils/validation.py
"""

import yaml
from typing import Dict, List, Any
from pydantic import BaseModel, ValidationError


class PackageMetadata(BaseModel):
    """Pydantic model for package metadata validation."""
    name: str
    version: str
    description: str
    author: str
    license: str
    qinter_version: str
    targets: List[str]
    tags: List[str] = []
    dependencies: List[str] = []
    homepage: str = None
    repository: str = None


class ExplanationCondition(BaseModel):
    """Validation for explanation conditions."""
    exception_type: str
    message_patterns: List[str]
    context_conditions: List[Dict[str, Any]] = []


class ExplanationContent(BaseModel):
    """Validation for explanation content."""
    title: str
    description: str
    suggestions: List[Dict[str, Any]]
    examples: List[Dict[str, Any]] = []


class Explanation(BaseModel):
    """Validation for individual explanations."""
    id: str
    priority: int
    conditions: ExplanationCondition
    explanation: ExplanationContent


class PackageStructure(BaseModel):
    """Complete package structure validation."""
    metadata: PackageMetadata
    explanations: List[Explanation]


def validate_package_yaml(yaml_content: str) -> Dict[str, Any]:
    """
    Validate YAML package content against Qinter standards.
    
    Args:
        yaml_content: Raw YAML content as string
        
    Returns:
        Parsed and validated package data
        
    Raises:
        ValueError: If validation fails
    """
    # Parse YAML
    try:
        data = yaml.safe_load(yaml_content)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML format: {e}")
    
    # Validate structure
    try:
        validated_package = PackageStructure(**data)
        return validated_package.model_dump()
    except ValidationError as e:
        raise ValueError(f"Package validation failed: {e}")


def validate_package_name(name: str) -> bool:
    """
    Validate package name format.
    
    Args:
        name: Package name to validate
        
    Returns:
        True if valid, False otherwise
    """
    import re
    
    # Package name rules:
    # - 3-50 characters
    # - lowercase letters, numbers, hyphens
    # - must start with letter
    # - no consecutive hyphens
    pattern = r'^[a-z][a-z0-9]*(-[a-z0-9]+)*$'
    
    return (
        len(name) >= 3 and 
        len(name) <= 50 and 
        re.match(pattern, name) is not None
    )


def validate_semantic_version(version: str) -> bool:
    """
    Validate semantic version format.
    
    Args:
        version: Version string to validate
        
    Returns:
        True if valid semantic version
    """
    import re
    
    # Semantic version pattern: MAJOR.MINOR.PATCH
    pattern = r'^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$'
    
    return re.match(pattern, version) is not None


def get_validation_errors(yaml_content: str) -> List[str]:
    """
    Get list of validation errors for a package.
    
    Args:
        yaml_content: YAML content to validate
        
    Returns:
        List of error messages (empty if valid)
    """
    errors = []
    
    try:
        data = yaml.safe_load(yaml_content)
    except yaml.YAMLError as e:
        return [f"Invalid YAML format: {e}"]
    
    # Check required top-level keys
    if 'metadata' not in data:
        errors.append("Missing 'metadata' section")
    if 'explanations' not in data:
        errors.append("Missing 'explanations' section")
    
    if errors:
        return errors
    
    # Validate metadata
    metadata = data.get('metadata', {})
    required_metadata = ['name', 'version', 'description', 'author', 'license', 'qinter_version', 'targets']
    
    for field in required_metadata:
        if field not in metadata:
            errors.append(f"Missing required metadata field: {field}")
    
    # Validate package name
    if 'name' in metadata and not validate_package_name(metadata['name']):
        errors.append("Invalid package name format")
    
    # Validate version
    if 'version' in metadata and not validate_semantic_version(metadata['version']):
        errors.append("Invalid semantic version format")
    
    # Validate explanations
    explanations = data.get('explanations', [])
    if not isinstance(explanations, list):
        errors.append("Explanations must be a list")
    elif len(explanations) == 0:
        errors.append("At least one explanation is required")
    else:
        for i, explanation in enumerate(explanations):
            if not isinstance(explanation, dict):
                errors.append(f"Explanation {i+1} must be an object")
                continue
            
            # Required explanation fields
            required_exp_fields = ['id', 'priority', 'conditions', 'explanation']
            for field in required_exp_fields:
                if field not in explanation:
                    errors.append(f"Explanation {i+1} missing required field: {field}")
    
    return errors