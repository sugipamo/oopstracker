"""
Function classification service for OOPStracker.
Handles function taxonomy analysis and classification.
"""

import logging
from typing import List, Optional, Dict, Any, Tuple
import asyncio

from ..models import CodeRecord


class ClassificationService:
    """Service for classifying functions using taxonomy analysis."""
    
    def __init__(self, detector, logger: Optional[logging.Logger] = None):
        """Initialize the classification service.
        
        Args:
            detector: The AST SimHash detector instance
            logger: Optional logger instance
        """
        self.detector = detector
        self.logger = logger or logging.getLogger(__name__)
        self._taxonomy_expert = None
        
    async def _get_taxonomy_expert(self):
        """Lazy load the taxonomy expert."""
        if self._taxonomy_expert is None:
            # Import here to avoid circular imports
            from ..function_taxonomy_expert import FunctionTaxonomyExpert
            self._taxonomy_expert = FunctionTaxonomyExpert(enable_ai=True)
        return self._taxonomy_expert
        
    async def classify_functions(self, 
                               verbose: bool = False,
                               limit: Optional[int] = 15) -> Dict[str, Any]:
        """Classify functions in the project.
        
        Args:
            verbose: Show detailed analysis for each function
            limit: Maximum number of functions to analyze
            
        Returns:
            Dictionary containing classification results and statistics
        """
        self.logger.info("Function Classification Analysis")
        
        # Get taxonomy expert
        taxonomy_expert = await self._get_taxonomy_expert()
        
        # Get all functions from detector
        function_units = [unit for unit in self.detector.code_units.values() 
                        if unit.type == 'function']
        
        if not function_units:
            return {
                'total_functions': 0,
                'analyzed_functions': 0,
                'classification_results': [],
                'category_counts': {},
                'insights': {}
            }
            
        total_functions = len(function_units)
        # Limit analysis for performance
        analysis_limit = min(limit, total_functions) if limit else total_functions
        
        self.logger.info(f"Analyzing {analysis_limit} functions (of {total_functions} total)...")
        
        # Analyze functions in batches
        function_data = [(unit.source_code, unit.name) for unit in function_units[:analysis_limit]]
        classification_results = await taxonomy_expert.analyze_function_collection(function_data)
        
        # Collect statistics
        category_counts = {}
        detailed_results = []
        
        for i, result in enumerate(classification_results):
            unit = function_units[i]
            category = result.primary_category
            category_counts[category] = category_counts.get(category, 0) + 1
            
            detailed_results.append({
                'unit': unit,
                'result': result,
                'name': unit.name,
                'file_path': unit.file_path,
                'category': result.primary_category,
                'confidence': result.confidence,
                'methods': result.analysis_methods,
                'alternatives': result.alternative_categories
            })
            
        # Get expert insights
        insights = taxonomy_expert.get_expert_insights()
        
        return {
            'total_functions': total_functions,
            'analyzed_functions': len(classification_results),
            'classification_results': classification_results,
            'detailed_results': detailed_results,
            'category_counts': category_counts,
            'insights': insights,
            'verbose': verbose
        }
        
    def format_classification_results(self, results: Dict[str, Any]) -> str:
        """Format classification results for display.
        
        Args:
            results: Classification results dictionary
            
        Returns:
            Formatted string for display
        """
        lines = []
        
        if results['analyzed_functions'] == 0:
            lines.append("   No functions found for classification")
            return "\n".join(lines)
            
        # Verbose output
        if results.get('verbose'):
            for detail in results['detailed_results']:
                lines.append(f"\n   📝 {detail['name']} ({detail['file_path']})")
                lines.append(f"      Category: {detail['category']} (confidence: {detail['confidence']:.2f})")
                lines.append(f"      Methods: {', '.join(detail['methods'])}")
                if detail['alternatives']:
                    alts = ', '.join([f"{cat}({conf:.2f})" for cat, conf in detail['alternatives']])
                    lines.append(f"      Alternatives: {alts}")
        
        # Summary
        lines.append(f"\n   📊 Classification Summary:")
        category_counts = results['category_counts']
        analyzed_count = results['analyzed_functions']
        
        for category, count in sorted(category_counts.items()):
            percentage = (count / analyzed_count) * 100
            lines.append(f"      {category}: {count} functions ({percentage:.1f}%)")
        
        # Performance metrics
        insights = results.get('insights', {})
        if 'performance_metrics' in insights:
            avg_time = insights['performance_metrics']['average_processing_time']
            lines.append(f"      Average processing time: {avg_time:.3f}s")
            
        # Tips
        if results['total_functions'] > results['analyzed_functions']:
            lines.append(f"      💡 Use --verbose to see detailed analysis of each function")
            
        return "\n".join(lines)
        
    async def classify_single_function(self, code: str, name: str) -> Dict[str, Any]:
        """Classify a single function.
        
        Args:
            code: Function source code
            name: Function name
            
        Returns:
            Classification result dictionary
        """
        taxonomy_expert = await self._get_taxonomy_expert()
        result = await taxonomy_expert.analyze_function(code, name)
        
        return {
            'category': result.primary_category,
            'confidence': result.confidence,
            'methods': result.analysis_methods,
            'alternatives': result.alternative_categories
        }