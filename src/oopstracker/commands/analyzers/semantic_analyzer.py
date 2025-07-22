"""
Semantic analysis analyzer.
"""

from typing import List, Dict, Any, Optional
from .base import BaseAnalyzer, AnalysisResult
from ...models import CodeRecord
from ...akinator_classifier import AkinatorClassifier


class SemanticAnalyzer(BaseAnalyzer):
    """Analyzer for semantic code analysis."""
    
    async def analyze(self, duplicates: List[Any] = None, **kwargs) -> AnalysisResult:
        """Perform semantic analysis."""
        if not self.semantic_detector:
            return AnalysisResult(
                success=False,
                data={},
                summary="Semantic detector not available",
                errors=["Semantic analysis requires AI configuration"]
            )
        
        try:
            # Convert structural duplicates to CodeRecords for semantic analysis
            code_records = []
            
            if duplicates:
                for record1, record2, similarity in duplicates[:10]:  # Limit to top 10
                    code_records.extend([record1, record2])
            
            # Remove duplicates while preserving order
            seen = set()
            unique_records = []
            for record in code_records:
                if record.id not in seen:
                    seen.add(record.id)
                    unique_records.append(record)
            
            # Perform semantic analysis
            semantic_results = await self.semantic_detector.analyze_code_collection(
                unique_records[:20]  # Limit analysis
            )
            
            # Process Akinator classification if available
            akinator_results = None
            if semantic_results.get('semantic_duplicates'):
                akinator_results = await self._run_akinator_analysis(
                    semantic_results['semantic_duplicates']
                )
            
            return AnalysisResult(
                success=True,
                data={
                    'semantic_results': semantic_results,
                    'akinator_results': akinator_results,
                    'record_count': len(unique_records)
                },
                summary=f"Analyzed {len(unique_records)} code units semantically"
            )
            
        except Exception as e:
            return AnalysisResult(
                success=False,
                data={},
                summary="Semantic analysis failed",
                errors=[str(e)]
            )
    
    async def _run_akinator_analysis(self, semantic_duplicates: List[Any]) -> Optional[Dict[str, Any]]:
        """Run Akinator classification on semantic duplicates."""
        try:
            classifier = AkinatorClassifier(enable_ai=True)
            
            # Analyze duplicates
            classification_results = []
            for dup in semantic_duplicates[:5]:  # Limit to top 5
                result = await classifier.classify_semantic_duplicate(dup)
                classification_results.append(result)
            
            # Get insights
            insights = classifier.get_classification_insights()
            
            return {
                'classifications': classification_results,
                'insights': insights
            }
        except Exception as e:
            self.context.logger.error(f"Akinator analysis failed: {e}")
            return None
    
    def display_results(self, result: AnalysisResult) -> None:
        """Display semantic analysis results."""
        if not result.success:
            print(f"\n❌ Semantic analysis failed: {', '.join(result.errors)}")
            return
        
        print(f"\n🧠 Performing semantic analysis...")
        
        data = result.data
        semantic_results = data.get('semantic_results', {})
        
        # Display semantic duplicates
        semantic_duplicates = semantic_results.get('semantic_duplicates', [])
        if semantic_duplicates:
            print(f"\n🎯 Found {len(semantic_duplicates)} semantic duplicate groups:")
            for i, sem_dup in enumerate(semantic_duplicates[:5], 1):
                print(self._format_semantic_duplicate(sem_dup, i))
        else:
            print("   No semantic duplicates found")
        
        # Display semantic summary
        self._display_semantic_summary(semantic_results)
        
        # Display intent tree analysis
        if 'intent_trees' in semantic_results:
            self._display_intent_tree_analysis(semantic_results)
        
        # Display Akinator results
        akinator_results = data.get('akinator_results')
        if akinator_results:
            self._display_akinator_results(akinator_results)
    
    def _format_semantic_duplicate(self, sem_dup: Any, index: int) -> str:
        """Format semantic duplicate for display."""
        output = f"\n   {index}. Semantic Group (confidence: {sem_dup.confidence:.2f}):"
        output += f"\n      Intent: {sem_dup.semantic_intent}"
        output += f"\n      Functions: {len(sem_dup.functions)}"
        
        for j, func in enumerate(sem_dup.functions[:3], 1):
            func_name = func.get('name', 'Unknown')
            func_file = self.format_file_path(func.get('file_path', 'Unknown'))
            output += f"\n      {j}. {func_name} ({func_file})"
        
        if len(sem_dup.functions) > 3:
            output += f"\n      ... and {len(sem_dup.functions) - 3} more functions"
        
        return output
    
    def _display_semantic_summary(self, semantic_results: Dict[str, Any]):
        """Display semantic analysis summary."""
        summary = semantic_results.get('analysis_summary', {})
        if summary:
            print(f"\n📊 Semantic Analysis Summary:")
            
            if 'total_functions_analyzed' in summary:
                print(f"   Functions analyzed: {summary['total_functions_analyzed']}")
            if 'unique_intents' in summary:
                print(f"   Unique intents found: {summary['unique_intents']}")
            if 'semantic_duplicate_groups' in summary:
                print(f"   Semantic duplicate groups: {summary['semantic_duplicate_groups']}")
            if 'average_confidence' in summary:
                print(f"   Average confidence: {summary['average_confidence']:.2f}")
    
    def _display_intent_tree_analysis(self, semantic_results: Dict[str, Any]):
        """Display intent tree analysis results."""
        intent_trees = semantic_results.get('intent_trees', {})
        if intent_trees and 'hierarchy' in intent_trees:
            print(f"\n🌳 Intent Tree Analysis:")
            hierarchy = intent_trees['hierarchy']
            
            for category, intents in list(hierarchy.items())[:3]:
                print(f"   {category}:")
                for intent, count in list(intents.items())[:3]:
                    print(f"      - {intent}: {count} functions")
    
    def _display_akinator_results(self, akinator_results: Dict[str, Any]):
        """Display Akinator classification results."""
        if not akinator_results:
            return
        
        print(f"\n🎮 Akinator Pattern Classification:")
        
        classifications = akinator_results.get('classifications', [])
        for i, classification in enumerate(classifications[:3], 1):
            if classification.get('success'):
                pattern = classification.get('pattern_type', 'Unknown')
                confidence = classification.get('confidence', 0)
                print(f"   {i}. Pattern: {pattern} (confidence: {confidence:.2f})")
                if 'reasoning' in classification:
                    print(f"      Reasoning: {classification['reasoning']}")
        
        insights = akinator_results.get('insights', {})
        if insights:
            patterns = insights.get('pattern_distribution', {})
            if patterns:
                print(f"\n   Pattern Distribution:")
                for pattern, data in patterns.items():
                    count = data.get('count', 0)
                    avg_conf = data.get('average_confidence', 0)
                    print(f"      {pattern}: {count} occurrences (avg confidence: {avg_conf:.2f})")