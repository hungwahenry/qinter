"""
qinter/explanations/pattern_matcher.py

This module matches errors against explanation patterns and selects
the most appropriate explanation based on context and priority.
"""

import re
from typing import Any, Dict, List, Optional, Tuple
from qinter.packages.loader import Explanation, ExplanationPack, ContextCondition
from qinter.explanations.context_analyzer import get_analyzer


class PatternMatcher:
    """Matches errors against explanation patterns."""
    
    def __init__(self):
        self.loaded_explanations: List[Tuple[Explanation, ExplanationPack]] = []
        self.context_analyzer = get_analyzer()
    
    def load_explanations(self, packs: List[ExplanationPack]) -> None:
        """
        Load explanations from multiple packs.
        
        Args:
            packs: List of explanation packs to load
        """
        self.loaded_explanations.clear()
        
        for pack in packs:
            for explanation in pack.explanations:
                self.loaded_explanations.append((explanation, pack))
        
        # Sort by priority (higher priority first)
        self.loaded_explanations.sort(key=lambda x: x[0].priority, reverse=True)
    
    def find_best_explanation(
        self, 
        exception: Exception, 
        context: Dict[str, Any]
    ) -> Optional[Tuple[Explanation, ExplanationPack, Dict[str, Any]]]:
        """
        Find the best explanation for the given exception.
        
        Args:
            exception: The Python exception that occurred
            context: Context information from the interceptor
            
        Returns:
            Tuple of (explanation, pack, analysis) or None if no match found
        """
        exception_type = type(exception).__name__
        exception_message = str(exception)
        
        # Perform context analysis
        analysis = self.context_analyzer.analyze(exception, context)
        
        # Find matching explanations
        for explanation, pack in self.loaded_explanations:
            if self._matches_explanation(explanation, exception_type, exception_message, analysis):
                return explanation, pack, analysis
        
        return None
    
    def find_all_matching_explanations(
        self, 
        exception: Exception, 
        context: Dict[str, Any]
    ) -> List[Tuple[Explanation, ExplanationPack, Dict[str, Any]]]:
        """
        Find all explanations that match the given exception.
        
        Args:
            exception: The Python exception that occurred
            context: Context information from the interceptor
            
        Returns:
            List of (explanation, pack, analysis) tuples, sorted by priority
        """
        exception_type = type(exception).__name__
        exception_message = str(exception)
        
        # Perform context analysis
        analysis = self.context_analyzer.analyze(exception, context)
        
        matches = []
        for explanation, pack in self.loaded_explanations:
            if self._matches_explanation(explanation, exception_type, exception_message, analysis):
                matches.append((explanation, pack, analysis))
        
        return matches
    
    def _matches_explanation(
        self, 
        explanation: Explanation, 
        exception_type: str, 
        exception_message: str,
        analysis: Dict[str, Any]
    ) -> bool:
        """
        Check if an explanation matches the given exception.
        
        Args:
            explanation: The explanation to check
            exception_type: Type of the exception
            exception_message: Exception message
            analysis: Context analysis results
            
        Returns:
            True if the explanation matches, False otherwise
        """
        conditions = explanation.conditions
        
        # Check exception type
        if conditions.exception_type != exception_type:
            return False
        
        # Check message patterns
        if not self._matches_message_patterns(conditions.message_patterns, exception_message):
            return False
        
        # Check context conditions
        if conditions.context_conditions:
            if not self._matches_context_conditions(conditions.context_conditions, analysis):
                return False
        
        return True
    
    def _matches_message_patterns(self, patterns: List[str], message: str) -> bool:
        """Check if any message pattern matches the exception message."""
        for pattern in patterns:
            try:
                if re.search(pattern, message, re.IGNORECASE):
                    return True
            except re.error:
                # Skip invalid regex patterns
                continue
        return False
    
    def _matches_context_conditions(
        self, 
        conditions: List[ContextCondition], 
        analysis: Dict[str, Any]
    ) -> bool:
        """Check if all context conditions are met."""
        for condition in conditions:
            if not self.context_analyzer.check_condition(condition, analysis):
                return False
        return True
    
    def get_loaded_explanation_count(self) -> int:
        """Get the number of loaded explanations."""
        return len(self.loaded_explanations)
    
    def get_explanations_for_exception_type(self, exception_type: str) -> List[Explanation]:
        """Get all explanations that handle a specific exception type."""
        matches = []
        for explanation, pack in self.loaded_explanations:
            if explanation.conditions.exception_type == exception_type:
                matches.append(explanation)
        return matches


# Global pattern matcher instance
_matcher = PatternMatcher()

def get_matcher() -> PatternMatcher:
    """Get the global pattern matcher instance."""
    return _matcher

def find_explanation(
    exception: Exception, 
    context: Dict[str, Any]
) -> Optional[Tuple[Explanation, ExplanationPack, Dict[str, Any]]]:
    """Convenience function to find the best explanation."""
    return _matcher.find_best_explanation(exception, context)