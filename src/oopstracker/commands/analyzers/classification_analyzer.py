"""
Function classification analyzer.
"""

from typing import List, Dict, Any
from .base import BaseAnalyzer, AnalysisResult
from ...function_taxonomy_expert import FunctionTaxonomyExpert


class ClassificationAnalyzer(BaseAnalyzer):
    """Analyzer for function classification."""
    
    async def analyze(self, **kwargs) -> AnalysisResult:
        """Perform function classification analysis."""
        taxonomy_expert = FunctionTaxonomyExpert(enable_ai=True)
        
        # Get all functions from detector
        function_units = [unit for unit in self.detector.code_units.values() 
                         if unit.type == 'function']
        
        if not function_units:
            return AnalysisResult(
                success=True,
                data={},
                summary="No functions found for classification"
            )
        
        total_functions = len(function_units)
        # Limit analysis for performance - analyze top 15 functions
        analysis_limit = min(15, total_functions)
        
        # Analyze functions in batches
        function_data = [(unit.source_code, unit.name) 
                        for unit in function_units[:analysis_limit]]
        classification_results = await taxonomy_expert.analyze_function_collection(function_data)
        
        # Collect category counts
        category_counts = {}
        detailed_results = []
        
        for i, result in enumerate(classification_results):
            unit = function_units[i]
            category = result.primary_category
            category_counts[category] = category_counts.get(category, 0) + 1
            
            detailed_results.append({
                'unit': unit,
                'result': result
            })
        
        # Get expert insights
        insights = taxonomy_expert.get_expert_insights()
        
        return AnalysisResult(
            success=True,
            data={
                'total_functions': total_functions,
                'analyzed_functions': analysis_limit,
                'category_counts': category_counts,
                'detailed_results': detailed_results,
                'insights': insights
            },
            summary=f"Analyzed {analysis_limit} of {total_functions} functions"
        )
    
    def display_results(self, result: AnalysisResult) -> None:
        """Display classification results."""
        data = result.data
        
        print(f"\n🎯 Function Classification Analysis")
        
        if not data:
            print("   No functions found for classification")
            return
        
        print(f"   Analyzing {data['analyzed_functions']} functions (of {data['total_functions']} total)...")
        
        # Display detailed results if verbose
        if hasattr(self.args, 'verbose') and self.args.verbose:
            for item in data['detailed_results']:
                unit = item['unit']
                result = item['result']
                print(f"\n   📝 {unit.name} ({unit.file_path})")
                print(f"      Category: {result.primary_category} (confidence: {result.confidence:.2f})")
                print(f"      Methods: {', '.join(result.analysis_methods)}")
                if result.alternative_categories:
                    alts = ', '.join([f"{cat}({conf:.2f})" for cat, conf in result.alternative_categories])
                    print(f"      Alternatives: {alts}")
        
        # Summary
        print(f"\n   📊 Classification Summary:")
        category_counts = data['category_counts']
        analyzed_count = data['analyzed_functions']
        
        for category, count in sorted(category_counts.items()):
            percentage = (count / analyzed_count) * 100
            print(f"      {category}: {count} functions ({percentage:.1f}%)")
        
        # Expert insights
        insights = data.get('insights', {})
        if 'performance_metrics' in insights:
            avg_time = insights['performance_metrics']['average_processing_time']
            print(f"      Average processing time: {avg_time:.3f}s")
        
        if data['total_functions'] > data['analyzed_functions']:
            print(f"      💡 Use --verbose to see detailed analysis of each function")