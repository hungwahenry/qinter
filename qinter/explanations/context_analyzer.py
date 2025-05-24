"""
qinter/explanations/context_analyzer.py

This module analyzes error context to provide intelligent suggestions
and variable substitutions for explanation templates.
"""

import re
from difflib import get_close_matches
from typing import Any, Dict, List, Optional, Set
from qinter.packages.loader import ContextCondition


class ContextAnalyzer:
    """Analyzes error context to enable smart explanations."""
    
    def __init__(self):
        # Common module names that look like imports
        self.common_modules = {
            'requests', 'pandas', 'numpy', 'matplotlib', 'json', 'os', 'sys', 
            'datetime', 'math', 'random', 'time', 'urllib', 'sqlite3', 'csv',
            'pickle', 'itertools', 'collections', 'functools', 'operator'
        }
        
        # Common builtin function typos
        self.builtin_typos = {
            'lenght': 'len', 'lentgh': 'len', 'legth': 'len',
            'pirnt': 'print', 'prnit': 'print', 'prin': 'print',
            'strig': 'str', 'strign': 'str',
            'itn': 'int', 'itne': 'int',
            'flaot': 'float', 'flot': 'float',
            'lsit': 'list', 'listst': 'list',
            'dcit': 'dict', 'dictionairy': 'dict'
        }
    
    def analyze(self, exception: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform comprehensive context analysis.
        
        Args:
            exception: The Python exception that occurred
            context: Context information from the interceptor
            
        Returns:
            Dictionary with analysis results and template variables
        """
        traceback_info = context.get('traceback_info', [])
        analysis = {
            # Basic extraction
            'variable_name': self._extract_variable_name(exception),
            'exception_type': type(exception).__name__,
            'exception_message': str(exception),
            'filename': context.get('file_context', {}).get('filename', 'interactive'),
            'line_number': context.get('file_context', {}).get('error_line', 0),
            'function_name': traceback_info[-1].get('function_name', 'module') if traceback_info else 'module',
                        
            # Advanced analysis
            'available_variables': self._get_available_variables(context),
            'imported_modules': self._get_imported_modules(context),
            'similar_variables': [],
            'closest_variable': None,
            'similarity_score': 0.0,
            
            # Pattern detection
            'looks_like_import': False,
            'builtin_typo_detected': False,
            'correct_builtin': None,
            'similar_variables_exist': False,
            
            # Type-specific analysis
            'object_type': self._extract_object_type(exception),
            'operation': self._extract_operation(exception),
            'type1': None,
            'type2': None,
            'expected': None,
            'actual': None,
            'bad_value': self._extract_bad_value(exception),
        }
        
        # Perform specific analyses
        self._analyze_variable_similarity(analysis)
        self._analyze_import_patterns(analysis)
        self._analyze_builtin_typos(analysis)
        self._analyze_type_errors(analysis, exception)
        self._analyze_value_errors(analysis, exception)
        
        return analysis
    
    def check_condition(self, condition: ContextCondition, analysis: Dict[str, Any]) -> bool:
        """
        Check if a context condition is met.
        
        Args:
            condition: The condition to check
            analysis: Results from context analysis
            
        Returns:
            True if condition is met, False otherwise
        """
        if condition.type == "variable_similarity":
            threshold = condition.threshold or 0.6
            min_matches = condition.min_matches or 1
            return (analysis['similarity_score'] >= threshold and 
                   len(analysis['similar_variables']) >= min_matches)
        
        elif condition.type == "import_pattern":
            if not condition.modules:
                return analysis['looks_like_import']
            return (analysis['looks_like_import'] and 
                   analysis['variable_name'] in condition.modules)
        
        elif condition.type == "builtin_typo":
            if not condition.functions:
                return analysis['builtin_typo_detected']
            return (analysis['builtin_typo_detected'] and 
                   analysis['correct_builtin'] in condition.functions)
        
        elif condition.type == "file_extension":
            filename = analysis['filename']
            if condition.extensions:
                return any(filename.endswith(ext) for ext in condition.extensions)
            return True
        
        elif condition.type == "function_context":
            inside_function = analysis['function_name'] != 'module'
            return inside_function == condition.inside_function
        
        # Add more condition types as needed
        return True
    
    def _extract_variable_name(self, exception: Exception) -> str:
        """Extract variable name from exception message."""
        message = str(exception)
        
        # NameError: name 'variable' is not defined
        match = re.search(r"name '([^']+)' is not defined", message)
        if match:
            return match.group(1)
        
        # TypeError: 'type' object is not callable
        match = re.search(r"'([^']+)' object is not callable", message)
        if match:
            return f"variable_of_type_{match.group(1)}"
        
        return "unknown"
    
    def _extract_object_type(self, exception: Exception) -> str:
        """Extract object type from TypeError messages."""
        message = str(exception)
        
        match = re.search(r"'([^']+)' object", message)
        if match:
            return match.group(1)
        
        return "unknown"
    
    def _extract_operation(self, exception: Exception) -> str:
        """Extract operation from TypeError messages."""
        message = str(exception)
        
        match = re.search(r"unsupported operand type\(s\) for (.+):", message)
        if match:
            return match.group(1).strip()
        
        return "operation"
    
    def _extract_bad_value(self, exception: Exception) -> str:
        """Extract bad value from ValueError messages."""
        message = str(exception)
        
        # invalid literal for int() with base 10: 'value'
        match = re.search(r"invalid literal for int\(\) with base \d+: '([^']*)'", message)
        if match:
            return match.group(1)
        
        return "value"
    
    def _get_available_variables(self, context: Dict[str, Any]) -> List[str]:
        """Get list of available variable names from context."""
        local_vars = context.get("local_variables", {})
        
        # Filter out internal Python variables
        available = [
            name for name in local_vars.keys() 
            if not name.startswith('_') and isinstance(name, str) and len(name) > 1
        ]
        
        return sorted(available)
    
    def _get_imported_modules(self, context: Dict[str, Any]) -> List[str]:
        """Get list of imported modules (simplified for now)."""
        # TODO: Implement actual import detection from file analysis
        return []
    
    def _analyze_variable_similarity(self, analysis: Dict[str, Any]) -> None:
        """Analyze variable name similarity for typo detection."""
        variable_name = analysis['variable_name']
        available_variables = analysis['available_variables']
        
        if not variable_name or not available_variables:
            return
        
        # Find similar variable names
        similar = get_close_matches(
            variable_name, 
            available_variables, 
            n=5, 
            cutoff=0.4
        )
        
        analysis['similar_variables'] = similar
        
        if similar:
            analysis['closest_variable'] = similar[0]
            analysis['similar_variables_exist'] = True
            
            # Calculate similarity score
            from difflib import SequenceMatcher
            similarity = SequenceMatcher(None, variable_name, similar[0]).ratio()
            analysis['similarity_score'] = similarity
    
    def _analyze_import_patterns(self, analysis: Dict[str, Any]) -> None:
        """Analyze if the variable looks like a missing import."""
        variable_name = analysis['variable_name']
        
        if variable_name.lower() in self.common_modules:
            analysis['looks_like_import'] = True
    
    def _analyze_builtin_typos(self, analysis: Dict[str, Any]) -> None:
        """Analyze if the variable looks like a misspelled builtin."""
        variable_name = analysis['variable_name']
        
        if variable_name.lower() in self.builtin_typos:
            analysis['builtin_typo_detected'] = True
            analysis['correct_builtin'] = self.builtin_typos[variable_name.lower()]
    
    def _analyze_type_errors(self, analysis: Dict[str, Any], exception: Exception) -> None:
        """Analyze TypeError-specific patterns."""
        if not isinstance(exception, TypeError):
            return
        
        message = str(exception)
        
        # Extract types from unsupported operand error
        match = re.search(r"unsupported operand type\(s\) for (.+): '([^']+)' and '([^']+)'", message)
        if match:
            operation, type1, type2 = match.groups()
            analysis['operation'] = operation.strip()
            analysis['type1'] = type1
            analysis['type2'] = type2
    
    def _analyze_value_errors(self, analysis: Dict[str, Any], exception: Exception) -> None:
        """Analyze ValueError-specific patterns."""
        if not isinstance(exception, ValueError):
            return
        
        message = str(exception)
        
        # Extract expected/actual from unpacking errors
        match = re.search(r"not enough values to unpack \(expected (\d+), got (\d+)\)", message)
        if match:
            analysis['expected'] = int(match.group(1))
            analysis['actual'] = int(match.group(2))
        
        match = re.search(r"too many values to unpack \(expected (\d+)\)", message)
        if match:
            analysis['expected'] = int(match.group(1))


# Global analyzer instance
_analyzer = ContextAnalyzer()

def get_analyzer() -> ContextAnalyzer:
    """Get the global context analyzer instance."""
    return _analyzer

def analyze_context(exception: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
    """Convenience function to analyze error context."""
    return _analyzer.analyze(exception, context)