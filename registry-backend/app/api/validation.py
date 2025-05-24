# Standard library imports
import io
from typing import Dict, List, Any

# Third-party imports
import yaml
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

# Local imports
from app.database.supabase import get_db
from app.utils.validation import validate_package_yaml, get_validation_errors

router = APIRouter()


@router.post("/validate")
async def validate_package(
    content: str = None,
    file: UploadFile = File(None)
):
    """
    Validate a package YAML file from content or uploaded file.
    
    Can validate from:
    - Direct YAML content in request body
    - Uploaded file
    """
    yaml_content = None
    source = None
    
    try:
        # Determine source and get content
        if content:
            yaml_content = content
            source = "direct_content"
        elif file:
            if not file.filename.endswith(('.yaml', '.yml')):
                raise HTTPException(status_code=400, detail="File must be a YAML file")
            
            content_bytes = await file.read()
            yaml_content = content_bytes.decode('utf-8')
            source = f"uploaded_file:{file.filename}"
        else:
            raise HTTPException(status_code=400, detail="Must provide content or file")
        
        if not yaml_content:
            raise HTTPException(status_code=400, detail="No content to validate")
        
        # Perform validation
        validation_result = await _validate_package_comprehensive(yaml_content)
        
        return {
            "valid": validation_result["valid"],
            "source": source,
            "errors": validation_result["errors"],
            "warnings": validation_result["warnings"],
            "metadata": validation_result.get("metadata"),
            "statistics": validation_result.get("statistics"),
            "suggestions": validation_result.get("suggestions", [])
        }
        
    except yaml.YAMLError as e:
        return {
            "valid": False,
            "source": source,
            "errors": [f"Invalid YAML syntax: {str(e)}"],
            "warnings": [],
            "suggestions": ["Check YAML syntax and formatting"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")

@router.post("/validate/batch")
async def validate_multiple_packages(
    files: List[UploadFile] = File(...)
):
    """Validate multiple package files at once."""
    results = []
    
    for file in files:
        try:
            if not file.filename.endswith(('.yaml', '.yml')):
                results.append({
                    "filename": file.filename,
                    "valid": False,
                    "errors": ["File must be a YAML file"],
                    "warnings": []
                })
                continue
            
            content_bytes = await file.read()
            yaml_content = content_bytes.decode('utf-8')
            
            validation_result = await _validate_package_comprehensive(yaml_content)
            validation_result["filename"] = file.filename
            results.append(validation_result)
            
        except Exception as e:
            results.append({
                "filename": file.filename,
                "valid": False,
                "errors": [f"Validation error: {str(e)}"],
                "warnings": []
            })
    
    # Summary statistics
    total = len(results)
    valid_count = sum(1 for r in results if r["valid"])
    
    return {
        "summary": {
            "total_files": total,
            "valid_files": valid_count,
            "invalid_files": total - valid_count,
            "success_rate": round((valid_count / total) * 100, 2) if total > 0 else 0
        },
        "results": results
    }


async def _validate_package_comprehensive(yaml_content: str) -> Dict[str, Any]:
    """Perform comprehensive package validation."""
    errors = []
    warnings = []
    suggestions = []
    metadata = None
    statistics = {}
    
    try:
        # Basic YAML parsing
        data = yaml.safe_load(yaml_content)
        
        # Use existing validation
        basic_errors = get_validation_errors(yaml_content)
        errors.extend(basic_errors)
        
        if not basic_errors:
            # Extract metadata for analysis
            metadata = data.get('metadata', {})
            explanations = data.get('explanations', [])
            
            # Advanced validation checks
            _validate_metadata_quality(metadata, warnings, suggestions)
            _validate_explanations_quality(explanations, warnings, suggestions, statistics)
            _validate_consistency(data, warnings, suggestions)
            
            # Calculate statistics
            statistics.update({
                "explanation_count": len(explanations),
                "target_exception_types": len(metadata.get('targets', [])),
                "total_suggestions": sum(len(exp.get('explanation', {}).get('suggestions', [])) for exp in explanations),
                "total_examples": sum(len(exp.get('explanation', {}).get('examples', [])) for exp in explanations),
                "has_dependencies": bool(metadata.get('dependencies')),
                "tag_count": len(metadata.get('tags', [])),
                "estimated_quality_score": _calculate_quality_score(data, len(warnings))
            })
    
    except yaml.YAMLError as e:
        errors.append(f"YAML parsing error: {str(e)}")
    except Exception as e:
        errors.append(f"Validation error: {str(e)}")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "suggestions": suggestions,
        "metadata": metadata,
        "statistics": statistics
    }


def _validate_metadata_quality(metadata: Dict[str, Any], warnings: List[str], suggestions: List[str]):
    """Validate metadata quality and provide suggestions."""
    
    # Check description quality
    description = metadata.get('description', '')
    if len(description) < 20:
        warnings.append("Description is very short (< 20 characters)")
        suggestions.append("Add a more detailed description explaining what errors this pack handles")
    elif len(description) > 200:
        warnings.append("Description is very long (> 200 characters)")
        suggestions.append("Consider shortening the description for better readability")
    
    # Check version format
    version = metadata.get('version', '')
    if version and not version.replace('.', '').replace('-', '').replace('alpha', '').replace('beta', '').isalnum():
        warnings.append("Version format appears non-standard")
        suggestions.append("Use semantic versioning (e.g., 1.0.0, 1.2.3-beta)")
    
    # Check tags
    tags = metadata.get('tags', [])
    if len(tags) == 0:
        warnings.append("No tags provided")
        suggestions.append("Add relevant tags to help users discover your package")
    elif len(tags) > 10:
        warnings.append("Too many tags (> 10)")
        suggestions.append("Limit tags to the most relevant ones")
    
    # Check targets
    targets = metadata.get('targets', [])
    if len(targets) == 0:
        warnings.append("No target exception types specified")
        suggestions.append("Specify which Python exception types this pack handles")
    
    # Check optional fields
    if not metadata.get('homepage'):
        suggestions.append("Consider adding a homepage URL for documentation")
    if not metadata.get('repository'):
        suggestions.append("Consider adding a repository URL for source code")


def _validate_explanations_quality(explanations: List[Dict], warnings: List[str], suggestions: List[str], statistics: Dict):
    """Validate explanation quality."""
    
    if len(explanations) == 0:
        warnings.append("No explanations provided")
        return
    
    priority_count = {}
    total_suggestions = 0
    total_examples = 0
    
    for i, explanation in enumerate(explanations):
        exp_id = explanation.get('id', f'explanation_{i}')
        
        # Check explanation structure
        if not explanation.get('priority'):
            warnings.append(f"Explanation '{exp_id}' missing priority")
        else:
            priority = explanation['priority']
            priority_count[priority] = priority_count.get(priority, 0) + 1
        
        # Check conditions
        conditions = explanation.get('conditions', {})
        if not conditions.get('exception_type'):
            warnings.append(f"Explanation '{exp_id}' missing exception_type")
        
        message_patterns = conditions.get('message_patterns', [])
        if not message_patterns:
            warnings.append(f"Explanation '{exp_id}' has no message patterns")
        
        # Check explanation content
        content = explanation.get('explanation', {})
        if not content.get('title'):
            warnings.append(f"Explanation '{exp_id}' missing title")
        
        if not content.get('description'):
            warnings.append(f"Explanation '{exp_id}' missing description")
        
        # Count suggestions and examples
        suggestions_list = content.get('suggestions', [])
        examples_list = content.get('examples', [])
        
        total_suggestions += len(suggestions_list)
        total_examples += len(examples_list)
        
        if len(suggestions_list) == 0:
            warnings.append(f"Explanation '{exp_id}' has no suggestions")
        
        if len(examples_list) == 0:
            suggestions.append(f"Consider adding code examples to explanation '{exp_id}'")
    
    # Check for duplicate priorities
    for priority, count in priority_count.items():
        if count > 1:
            warnings.append(f"Multiple explanations have priority {priority}")
            suggestions.append("Use unique priorities to ensure consistent explanation ordering")
    
    # Update statistics
    statistics.update({
        "avg_suggestions_per_explanation": round(total_suggestions / len(explanations), 2),
        "avg_examples_per_explanation": round(total_examples / len(explanations), 2),
        "priority_distribution": priority_count
    })


def _validate_consistency(data: Dict[str, Any], warnings: List[str], suggestions: List[str]):
    """Validate internal consistency."""
    
    metadata = data.get('metadata', {})
    explanations = data.get('explanations', [])
    
    # Check if explanation targets match metadata targets
    metadata_targets = set(metadata.get('targets', []))
    explanation_targets = set()
    
    for explanation in explanations:
        conditions = explanation.get('conditions', {})
        if conditions.get('exception_type'):
            explanation_targets.add(conditions['exception_type'])
    
    # Check for mismatches
    missing_from_metadata = explanation_targets - metadata_targets
    missing_from_explanations = metadata_targets - explanation_targets
    
    if missing_from_metadata:
        warnings.append(f"Exception types in explanations but not in metadata: {list(missing_from_metadata)}")
        suggestions.append("Update metadata targets to include all explained exception types")
    
    if missing_from_explanations:
        warnings.append(f"Exception types in metadata but no explanations: {list(missing_from_explanations)}")
        suggestions.append("Add explanations for all target exception types or remove from metadata")


def _calculate_quality_score(data: Dict[str, Any], warning_count: int) -> float:
    """Calculate a quality score for the package."""
    score = 100.0
    
    metadata = data.get('metadata', {})
    explanations = data.get('explanations', [])
    
    # Deduct points for warnings
    score -= warning_count * 5
    
    # Deduct points for missing optional fields
    if not metadata.get('homepage'):
        score -= 5
    if not metadata.get('repository'):
        score -= 5
    if not metadata.get('tags'):
        score -= 10
    
    # Add points for good practices
    if len(explanations) > 0:
        # Check if explanations have examples
        examples_count = sum(len(exp.get('explanation', {}).get('examples', [])) for exp in explanations)
        if examples_count > 0:
            score += 10
        
        # Check if explanations have multiple suggestions
        total_suggestions = sum(len(exp.get('explanation', {}).get('suggestions', [])) for exp in explanations)
        if total_suggestions >= len(explanations) * 2:  # At least 2 suggestions per explanation
            score += 10
    
    return max(0.0, min(100.0, score))