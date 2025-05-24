"""
qinter/explanations/template_renderer.py

This module handles variable substitution and conditional rendering
in explanation templates using context analysis results.
"""

import re
from typing import Any, Dict, List, Optional
from qinter.packages.loader import Explanation, ExplanationSuggestion, ExplanationExample


class TemplateRenderer:
    """Renders explanation templates with dynamic content."""
    
    def render_explanation(
        self, 
        explanation: Explanation, 
        analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Render a complete explanation with variable substitution.
        
        Args:
            explanation: The explanation to render
            analysis: Context analysis results for variable substitution
            
        Returns:
            Rendered explanation dictionary ready for display
        """
        rendered = {
            'title': self._render_template(explanation.explanation.title, analysis),
            'explanation': self._render_template(explanation.explanation.description, analysis),
            'suggestions': self._render_suggestions(explanation.explanation.suggestions, analysis),
            'examples': self._render_examples(explanation.explanation.examples, analysis),
            'metadata': {
                'explanation_id': explanation.id,
                'priority': explanation.priority,
            }
        }
        
        return rendered
    
    def _render_template(self, template: str, analysis: Dict[str, Any]) -> str:
        """
        Render a template string with variable substitution.
        
        Args:
            template: Template string with {variable} placeholders
            analysis: Variables for substitution
            
        Returns:
            Rendered string with variables substituted
        """
        if not template:
            return ""
        
        # Handle conditional blocks first
        rendered = self._handle_conditional_blocks(template, analysis)
        
        # Then handle variable substitution
        rendered = self._substitute_variables(rendered, analysis)
        
        return rendered.strip()
    
    def _handle_conditional_blocks(self, template: str, analysis: Dict[str, Any]) -> str:
        """Handle {if condition} blocks in templates."""
        # Simple implementation - could be expanded for more complex logic
        
        # Pattern: {if condition}content{else}alternative{endif}
        if_pattern = r'\{if\s+([^}]+)\}(.*?)\{endif\}'
        if_else_pattern = r'\{if\s+([^}]+)\}(.*?)\{else\}(.*?)\{endif\}'
        
        # Handle if-else blocks
        def replace_if_else(match):
            condition = match.group(1).strip()
            if_content = match.group(2)
            else_content = match.group(3)
            
            if self._evaluate_condition(condition, analysis):
                return if_content
            else:
                return else_content
        
        template = re.sub(if_else_pattern, replace_if_else, template, flags=re.DOTALL)
        
        # Handle simple if blocks
        def replace_if(match):
            condition = match.group(1).strip()
            content = match.group(2)
            
            if self._evaluate_condition(condition, analysis):
                return content
            else:
                return ""
        
        template = re.sub(if_pattern, replace_if, template, flags=re.DOTALL)
        
        return template
    
    def _evaluate_condition(self, condition: str, analysis: Dict[str, Any]) -> bool:
        """Evaluate a conditional expression."""
        # Simple condition evaluation
        # Could be expanded for more complex expressions
        
        # Direct boolean check
        if condition in analysis:
            value = analysis[condition]
            if isinstance(value, bool):
                return value
            elif isinstance(value, (list, str)):
                return len(value) > 0
            elif isinstance(value, (int, float)):
                return value > 0
        
        # Comparison operations (basic)
        if ' > ' in condition:
            left, right = condition.split(' > ', 1)
            left_val = analysis.get(left.strip(), 0)
            try:
                right_val = float(right.strip())
                return float(left_val) > right_val
            except (ValueError, TypeError):
                return False
        
        # Default to False for unknown conditions
        return False
    
    def _substitute_variables(self, template: str, analysis: Dict[str, Any]) -> str:
        """Substitute {variable} placeholders with actual values."""
        def replace_var(match):
            var_name = match.group(1)
            
            # Handle special formatting (like similarity_score:.0%)
            if ':' in var_name:
                var_name, format_spec = var_name.split(':', 1)
                value = analysis.get(var_name, f"{{unknown_variable_{var_name}}}")
                try:
                    if format_spec == '.0%':
                        return f"{float(value):.0%}"
                    elif format_spec.startswith('.') and format_spec.endswith('f'):
                        decimals = int(format_spec[1:-1])
                        return f"{float(value):.{decimals}f}"
                    else:
                        return str(value)
                except (ValueError, TypeError):
                    return str(value)
            else:
                value = analysis.get(var_name, f"{{unknown_variable_{var_name}}}")
                return str(value)
        
        # Replace {variable} patterns
        return re.sub(r'\{([^}]+)\}', replace_var, template)
    
    def _render_suggestions(
        self, 
        suggestions: List[ExplanationSuggestion], 
        analysis: Dict[str, Any]
    ) -> List[str]:
        """Render suggestion templates."""
        rendered_suggestions = []
        
        for suggestion in suggestions:
            # Check if condition is met
            if not self._should_include_item(suggestion.condition, analysis):
                continue
            
            rendered_text = self._render_template(suggestion.template, analysis)
            if rendered_text:  # Only include non-empty suggestions
                rendered_suggestions.append(rendered_text)
        
        # Sort by priority and return
        suggestions_with_priority = [
            (sugg, self._render_template(sugg.template, analysis))
            for sugg in suggestions
            if self._should_include_item(sugg.condition, analysis)
        ]
        
        suggestions_with_priority.sort(key=lambda x: x[0].priority)
        
        return [text for _, text in suggestions_with_priority if text]
    
    def _render_examples(
        self, 
        examples: List[ExplanationExample], 
        analysis: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """Render example templates."""
        rendered_examples = []
        
        for example in examples:
            # Check if condition is met
            if not self._should_include_item(example.condition, analysis):
                continue
            
            rendered_description = self._render_template(example.description, analysis)
            rendered_code = self._render_template(example.code, analysis)
            
            if rendered_description and rendered_code:
                rendered_examples.append({
                    'description': rendered_description,
                    'code': rendered_code,
                    'id': example.id
                })
        
        return rendered_examples
    
    def _should_include_item(self, condition: str, analysis: Dict[str, Any]) -> bool:
        """Check if an item should be included based on its condition."""
        if condition == "always":
            return True
        
        return self._evaluate_condition(condition, analysis)


# Global renderer instance
_renderer = TemplateRenderer()

def get_renderer() -> TemplateRenderer:
    """Get the global template renderer instance."""
    return _renderer

def render_explanation(
    explanation: Explanation, 
    analysis: Dict[str, Any]
) -> Dict[str, Any]:
    """Convenience function to render an explanation."""
    return _renderer.render_explanation(explanation, analysis)