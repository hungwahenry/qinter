"""
qinter/packages/loader.py

This module handles loading, parsing, and validating explanation packs
from YAML files according to the Qinter standard.
"""

import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass
from pydantic import BaseModel, ValidationError, validator
from qinter.utils.exceptions import PackageError


@dataclass
class PackMetadata:
    """Metadata for an explanation pack."""
    name: str
    version: str
    description: str
    author: str
    license: str
    qinter_version: str
    targets: List[str]
    tags: List[str] = None
    dependencies: List[str] = None
    homepage: str = None
    repository: str = None


@dataclass
class ContextCondition:
    """A condition that must be met based on error context."""
    type: str
    threshold: Optional[float] = None
    min_matches: Optional[int] = None
    modules: Optional[List[str]] = None
    functions: Optional[List[str]] = None
    extensions: Optional[List[str]] = None
    inside_function: Optional[bool] = None
    variable: Optional[str] = None
    expected_type: Optional[str] = None
    script: Optional[str] = None


@dataclass
class ExplanationConditions:
    """Conditions for when an explanation should be triggered."""
    exception_type: str
    message_patterns: List[str]
    context_conditions: List[ContextCondition] = None


@dataclass
class ExplanationSuggestion:
    """A suggestion for fixing an error."""
    template: str
    priority: int
    condition: str = "always"


@dataclass
class ExplanationExample:
    """A code example for fixing an error."""
    id: str
    description: str
    code: str
    condition: str = "always"


@dataclass
class ExplanationContent:
    """The actual explanation content."""
    title: str
    description: str
    suggestions: List[ExplanationSuggestion]
    examples: List[ExplanationExample]


@dataclass
class Explanation:
    """A complete explanation entry."""
    id: str
    priority: int
    conditions: ExplanationConditions
    explanation: ExplanationContent


@dataclass
class ExplanationPack:
    """A complete explanation pack."""
    metadata: PackMetadata
    explanations: List[Explanation]
    file_path: Optional[Path] = None


class YAMLPackLoader:
    """Loads and validates YAML explanation packs."""
    
    def __init__(self):
        self.loaded_packs: Dict[str, ExplanationPack] = {}
        self._validation_errors: List[str] = []
    
    def load_pack(self, file_path: Path) -> Optional[ExplanationPack]:
        """
        Load a single explanation pack from a YAML file.
        
        Args:
            file_path: Path to the YAML file
            
        Returns:
            ExplanationPack object or None if loading failed
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                raw_data = yaml.safe_load(f)
            
            # Validate the YAML structure
            pack = self._parse_and_validate(raw_data, file_path)
            
            if pack:
                pack.file_path = file_path
                self.loaded_packs[pack.metadata.name] = pack
                return pack
                
        except yaml.YAMLError as e:
            self._validation_errors.append(f"YAML parsing error in {file_path}: {e}")
        except FileNotFoundError:
            self._validation_errors.append(f"Pack file not found: {file_path}")
        except Exception as e:
            self._validation_errors.append(f"Unexpected error loading {file_path}: {e}")
        
        return None
    
    def load_packs_from_directory(self, directory: Path) -> List[ExplanationPack]:
        """
        Load all explanation packs from a directory.
        
        Args:
            directory: Directory containing YAML pack files
            
        Returns:
            List of successfully loaded packs
        """
        packs = []
        
        if not directory.exists():
            self._validation_errors.append(f"Directory not found: {directory}")
            return packs
        
        # Find all YAML files
        yaml_files = list(directory.glob("*.yaml")) + list(directory.glob("*.yml"))
        
        for yaml_file in yaml_files:
            pack = self.load_pack(yaml_file)
            if pack:
                packs.append(pack)
        
        return packs
    
    def load_core_packs(self) -> List[ExplanationPack]:
        """Load all core Python explanation packs."""
        # Get the core packs directory
        core_dir = Path(__file__).parent.parent.parent.parent / "explanation_packs" / "core"
        return self.load_packs_from_directory(core_dir)
    
    def _parse_and_validate(self, raw_data: Dict[str, Any], file_path: Path) -> Optional[ExplanationPack]:
        """Parse and validate raw YAML data into an ExplanationPack."""
        
        try:
            # Validate metadata
            metadata_dict = raw_data.get('metadata', {})
            metadata = self._parse_metadata(metadata_dict)
            
            # Validate explanations
            explanations_list = raw_data.get('explanations', [])
            explanations = []
            
            for i, exp_dict in enumerate(explanations_list):
                explanation = self._parse_explanation(exp_dict, i)
                if explanation:
                    explanations.append(explanation)
            
            if not explanations:
                self._validation_errors.append(f"No valid explanations found in {file_path}")
                return None
            
            return ExplanationPack(
                metadata=metadata,
                explanations=explanations
            )
            
        except Exception as e:
            self._validation_errors.append(f"Validation error in {file_path}: {e}")
            return None
    
    def _parse_metadata(self, metadata_dict: Dict[str, Any]) -> PackMetadata:
        """Parse and validate pack metadata."""
        
        required_fields = ['name', 'version', 'description', 'author', 'license', 'qinter_version', 'targets']
        
        for field in required_fields:
            if field not in metadata_dict:
                raise ValueError(f"Missing required metadata field: {field}")
        
        return PackMetadata(
            name=metadata_dict['name'],
            version=metadata_dict['version'],
            description=metadata_dict['description'],
            author=metadata_dict['author'],
            license=metadata_dict['license'],
            qinter_version=metadata_dict['qinter_version'],
            targets=metadata_dict['targets'],
            tags=metadata_dict.get('tags', []),
            dependencies=metadata_dict.get('dependencies', []),
            homepage=metadata_dict.get('homepage'),
            repository=metadata_dict.get('repository')
        )
    
    def _parse_explanation(self, exp_dict: Dict[str, Any], index: int) -> Optional[Explanation]:
        """Parse and validate a single explanation."""
        
        try:
            # Required fields
            required_fields = ['id', 'priority', 'conditions', 'explanation']
            for field in required_fields:
                if field not in exp_dict:
                    raise ValueError(f"Missing required explanation field: {field} (explanation {index})")
            
            # Parse conditions
            conditions = self._parse_conditions(exp_dict['conditions'])
            
            # Parse explanation content
            explanation_content = self._parse_explanation_content(exp_dict['explanation'])
            
            return Explanation(
                id=exp_dict['id'],
                priority=exp_dict['priority'],
                conditions=conditions,
                explanation=explanation_content
            )
            
        except Exception as e:
            self._validation_errors.append(f"Error parsing explanation {index}: {e}")
            return None
    
    def _parse_conditions(self, conditions_dict: Dict[str, Any]) -> ExplanationConditions:
        """Parse explanation conditions."""
        
        # Parse context conditions
        context_conditions = []
        if 'context_conditions' in conditions_dict:
            for cc_dict in conditions_dict['context_conditions']:
                context_condition = ContextCondition(
                    type=cc_dict['type'],
                    threshold=cc_dict.get('threshold'),
                    min_matches=cc_dict.get('min_matches'),
                    modules=cc_dict.get('modules'),
                    functions=cc_dict.get('functions'),
                    extensions=cc_dict.get('extensions'),
                    inside_function=cc_dict.get('inside_function'),
                    variable=cc_dict.get('variable'),
                    expected_type=cc_dict.get('expected_type'),
                    script=cc_dict.get('script')
                )
                context_conditions.append(context_condition)
        
        return ExplanationConditions(
            exception_type=conditions_dict['exception_type'],
            message_patterns=conditions_dict['message_patterns'],
            context_conditions=context_conditions
        )
    
    def _parse_explanation_content(self, content_dict: Dict[str, Any]) -> ExplanationContent:
        """Parse explanation content."""
        
        # Parse suggestions
        suggestions = []
        for sugg_dict in content_dict.get('suggestions', []):
            suggestion = ExplanationSuggestion(
                template=sugg_dict['template'],
                priority=sugg_dict['priority'],
                condition=sugg_dict.get('condition', 'always')
            )
            suggestions.append(suggestion)
        
        # Parse examples
        examples = []
        for ex_dict in content_dict.get('examples', []):
            example = ExplanationExample(
                id=ex_dict['id'],
                description=ex_dict['description'],
                code=ex_dict['code'],
                condition=ex_dict.get('condition', 'always')
            )
            examples.append(example)
        
        return ExplanationContent(
            title=content_dict['title'],
            description=content_dict['description'],
            suggestions=suggestions,
            examples=examples
        )
    
    def get_validation_errors(self) -> List[str]:
        """Get all validation errors that occurred during loading."""
        return self._validation_errors.copy()
    
    def clear_validation_errors(self) -> None:
        """Clear all validation errors."""
        self._validation_errors.clear()
    
    def get_loaded_packs(self) -> Dict[str, ExplanationPack]:
        """Get all successfully loaded packs."""
        return self.loaded_packs.copy()
    
    def get_packs_for_exception_type(self, exception_type: str) -> List[ExplanationPack]:
        """Get all packs that handle a specific exception type."""
        matching_packs = []
        
        for pack in self.loaded_packs.values():
            if exception_type in pack.metadata.targets:
                matching_packs.append(pack)
        
        return matching_packs


# Global loader instance
_loader = YAMLPackLoader()

def get_loader() -> YAMLPackLoader:
    """Get the global YAML pack loader instance."""
    return _loader

def load_core_packs() -> List[ExplanationPack]:
    """Convenience function to load core packs."""
    return _loader.load_core_packs()