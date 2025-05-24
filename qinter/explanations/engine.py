"""
qinter/explanations/engine.py
YAML-based explanation engine for Qinter.

This module coordinates between pattern matching, context analysis,
and template rendering to provide dynamic error explanations.
"""

from typing import Any, Dict, Optional
from qinter.packages.loader import get_loader, ExplanationPack
from qinter.explanations.pattern_matcher import get_matcher
from qinter.explanations.template_renderer import get_renderer


class ExplanationEngine:
    """Main engine for generating YAML-based error explanations."""
    
    def __init__(self) -> None:
        self.loader = get_loader()
        self.matcher = get_matcher()
        self.renderer = get_renderer()
        self._initialized = False
    
    def initialize(self) -> None:
        """Initialize the engine by loading core explanation packs."""
        if self._initialized:
            return
        
        # Load core Python explanation packs
        core_packs = self.loader.load_core_packs()
        
        if not core_packs:
            # Log warning about missing core packs
            print("⚠️  Warning: No core explanation packs found")
            return
        
        #Load user-installed packs
        from qinter.packages.manager import get_package_manager
        manager = get_package_manager()
        packages_dir = manager._get_packages_directory()
        user_packs = []
        
        if packages_dir.exists():
            user_packs = self.loader.load_packs_from_directory(packages_dir)
            
            # Combine all packs
            all_packs = core_packs + user_packs
            
            if not all_packs:
                print("⚠️  Warning: No explanation packs found")
                return
        
        # Load explanations into pattern matcher
        self.matcher.load_explanations(all_packs)
        
        self._initialized = True
        
        # Report loading success
        total_explanations = self.matcher.get_loaded_explanation_count()
        print(f"✅ Loaded {len(core_packs)} core + {len(user_packs)} user packs ({total_explanations} explanations)")
        
    def explain(self, exception: Exception, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Generate an explanation for the given exception.
        
        Args:
            exception: The Python exception that occurred
            context: Context information captured during the error
            
        Returns:
            Dictionary containing explanation details, or None if no explanation available
        """
        # Ensure engine is initialized
        if not self._initialized:
            self.initialize()
        
        try:
            # Find the best matching explanation
            match_result = self.matcher.find_best_explanation(exception, context)
            
            if not match_result:
                return None
            
            explanation, pack, analysis = match_result
            
            # Render the explanation with context
            rendered = self.renderer.render_explanation(explanation, analysis)
            
            # Add pack metadata
            rendered['metadata'].update({
                'pack_name': pack.metadata.name,
                'pack_version': pack.metadata.version,
                'pack_author': pack.metadata.author,
            })
            
            return rendered
            
        except Exception as e:
            # If explanation generation fails, return None
            print(f"⚠️  Error generating explanation: {e}")
            return None
    
    def reload_packs(self) -> None:
        """Reload all explanation packs."""
        self._initialized = False
        self.loader.loaded_packs.clear()
        self.matcher.loaded_explanations.clear()
        self.initialize()
    
    def load_additional_pack(self, pack_path: str) -> bool:
        """
        Load an additional explanation pack.
        
        Args:
            pack_path: Path to the YAML pack file
            
        Returns:
            True if loaded successfully, False otherwise
        """
        from pathlib import Path
        
        pack = self.loader.load_pack(Path(pack_path))
        if pack:
            # Add to pattern matcher
            current_packs = list(self.loader.loaded_packs.values())
            self.matcher.load_explanations(current_packs)
            return True
        return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about loaded explanations."""
        return {
            'loaded_packs': len(self.loader.loaded_packs),
            'total_explanations': self.matcher.get_loaded_explanation_count(),
            'exception_types_covered': list(set(
                explanation.conditions.exception_type 
                for explanation, _ in self.matcher.loaded_explanations
            )),
            'validation_errors': self.loader.get_validation_errors(),
        }


# Global engine instance
_engine = ExplanationEngine()

def explain_error(exception: Exception, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Main function to explain an error.
    
    This is the function called by the interceptor.
    """
    return _engine.explain(exception, context)

def get_engine() -> ExplanationEngine:
    """Get the global explanation engine instance."""
    return _engine

def initialize_engine() -> None:
    """Initialize the explanation engine."""
    _engine.initialize()