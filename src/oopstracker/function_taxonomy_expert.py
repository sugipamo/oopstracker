"""
Function Taxonomy Expert - Domain layer component for function classification.
Replaces the confusing "UnifiedClassificationEngine" naming.
"""

import asyncio
import logging
import re
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

from .ai_analysis_coordinator import get_ai_coordinator, AIAnalysisCoordinator
from .akinator_classifier import (
    ClassificationRule, ClassificationResult, FunctionCategory,
    AkinatorClassifier
)
from .progress_manager import ProgressManager
# REFACTORING: Extracted strategies for better separation of concerns
from .taxonomy_strategies.pattern_strategy import PatternAnalysisStrategy
from .taxonomy_strategies.structural_strategy import StructuralAnalysisStrategy
from .taxonomy_strategies.name_analyzer import FunctionNameAnalyzer


@dataclass
class TaxonomyResult:
    """Result of function taxonomy analysis."""
    primary_category: str
    confidence: float
    alternative_categories: List[Tuple[str, float]]
    analysis_methods: List[str]
    reasoning: str
    metadata: Dict[str, Any]
    processing_time: float


class AnalysisMethod(Enum):
    """Available analysis methods for function taxonomy."""
    PATTERN_MATCHING = "pattern_matching"
    AI_CLASSIFICATION = "ai_classification"
    STRUCTURAL_ANALYSIS = "structural_analysis"
    INTENT_RECOGNITION = "intent_recognition"
    HYBRID_APPROACH = "hybrid_approach"


class FunctionTaxonomyExpert:
    """
    Domain expert for function classification and taxonomy.
    
    This expert combines multiple analysis approaches to classify functions
    into a comprehensive taxonomy of software function types.
    """
    
    def __init__(self, enable_ai: bool = True):
        self.logger = logging.getLogger(__name__)
        
        # Domain services
        self.ai_coordinator = get_ai_coordinator() if enable_ai else None
        # REFACTORING: Using extracted strategy classes instead of internal methods
        self.pattern_strategy = PatternAnalysisStrategy()
        self.structural_strategy = StructuralAnalysisStrategy()
        self.name_analyzer = FunctionNameAnalyzer()
        
        # Domain knowledge
        self.classification_history: List[TaxonomyResult] = []
        self.expertise_metrics: Dict[str, float] = {}
        
        # Expert configuration
        self.enable_ai = enable_ai and (self.ai_coordinator is not None)
        self.confidence_threshold = 0.7
        self.max_alternatives = 3
        
        self.logger.info(f"Function taxonomy expert initialized (AI: {self.enable_ai})")
    
    async def classify_function_purpose(
        self, 
        function_code: str, 
        function_name: str = None,
        analysis_methods: List[AnalysisMethod] = None,
        domain_context: Dict[str, Any] = None
    ) -> TaxonomyResult:
        """
        Classify the purpose and type of a function.
        
        Args:
            function_code: The source code of the function
            function_name: Name of the function (optional)
            analysis_methods: Specific analysis methods to use
            domain_context: Additional domain context for classification
        
        Returns:
            TaxonomyResult with comprehensive taxonomy analysis
        """
        start_time = asyncio.get_event_loop().time()
        
        if analysis_methods is None:
            analysis_methods = [
                AnalysisMethod.PATTERN_MATCHING,
                AnalysisMethod.STRUCTURAL_ANALYSIS
            ]
            if self.enable_ai:
                analysis_methods.append(AnalysisMethod.AI_CLASSIFICATION)
        
        analysis_results = {}
        used_methods = []
        
        # Execute each analysis method
        for method in analysis_methods:
            try:
                method_start = asyncio.get_event_loop().time()
                
                if method == AnalysisMethod.PATTERN_MATCHING:
                    # REFACTORING: Using extracted pattern strategy
                    result = await self.pattern_strategy.analyze(function_code, function_name)
                    analysis_results[method.value] = result
                    used_methods.append(method.value)
                
                elif method == AnalysisMethod.AI_CLASSIFICATION and self.enable_ai:
                    self.logger.info(f"Starting AI classification for {function_name}")
                    result = await self._analyze_with_ai(function_code, function_name)
                    analysis_results[method.value] = result
                    used_methods.append(method.value)
                
                elif method == AnalysisMethod.STRUCTURAL_ANALYSIS:
                    # REFACTORING: Using extracted structural strategy
                    result = await self.structural_strategy.analyze(function_code, function_name)
                    analysis_results[method.value] = result
                    used_methods.append(method.value)
                
                method_elapsed = asyncio.get_event_loop().time() - method_start
                self.logger.info(f"Method {method.value} took {method_elapsed:.2f}s for {function_name}")
                
            except Exception as e:
                self.logger.error(f"Analysis method {method.value} failed: {e}")
        
        # Synthesize expert opinion
        taxonomy_result = self._synthesize_expert_opinion(
            analysis_results, used_methods, start_time
        )
        
        # Record for continuous learning
        self.classification_history.append(taxonomy_result)
        
        return taxonomy_result
    
    async def _analyze_with_patterns(self, function_code: str, function_name: str = None) -> Dict[str, Any]:
        """Analyze using established patterns and heuristics."""
        pattern_result = self.pattern_classifier.classify_function(function_code, function_name)
        
        return {
            "category": pattern_result.category,
            "confidence": pattern_result.confidence,
            "reasoning": pattern_result.reasoning,
            "matched_patterns": pattern_result.matched_rules,
            "method": "pattern_matching"
        }
    
    async def _analyze_with_ai(self, function_code: str, function_name: str = None) -> Dict[str, Any]:
        """Analyze using AI-powered classification."""
        categories = [category.value for category in FunctionCategory]
        
        ai_response = await self.ai_coordinator.classify_function(function_code, categories)
        
        return {
            "category": ai_response.result,
            "confidence": ai_response.confidence,
            "reasoning": ai_response.reasoning,
            "method": "ai_classification",
            "processing_time": ai_response.processing_time
        }
    
    async def _analyze_structure(self, function_code: str, function_name: str = None) -> Dict[str, Any]:
        """Analyze function structure and characteristics."""
        
        # Structural analysis
        lines = function_code.strip().split('\n')
        line_count = len(lines)
        
        # Code characteristics
        code_lower = function_code.lower()
        
        # Structural features
        has_return_value = 'return ' in function_code
        has_state_change = '=' in function_code and not '==' in function_code
        has_control_flow = any(keyword in code_lower for keyword in ['for ', 'while ', 'if ', 'elif '])
        has_async_operations = 'async def' in code_lower or 'await ' in code_lower
        has_error_handling = any(keyword in code_lower for keyword in ['try:', 'except', 'raise'])
        
        # Classify based on structure
        category = FunctionCategory.UNKNOWN.value
        confidence = 0.5
        structural_indicators = []
        
        if function_name:
            name_analysis = self.name_analyzer.analyze(function_name)
            category = name_analysis.get("suggested_category", category)
            confidence = name_analysis.get("confidence", confidence)
            structural_indicators.extend(name_analysis.get("indicators", []))
        
        # Refine based on structure
        if has_async_operations:
            if category == FunctionCategory.UNKNOWN.value:
                category = FunctionCategory.ASYNC_HANDLER.value
                confidence = 0.7
            structural_indicators.append("async operations detected")
        
        if has_error_handling:
            if category == FunctionCategory.UNKNOWN.value:
                category = FunctionCategory.ERROR_HANDLER.value
                confidence = 0.6
            structural_indicators.append("error handling present")
        
        if has_control_flow and line_count > 10:
            if category == FunctionCategory.UNKNOWN.value:
                category = FunctionCategory.BUSINESS_LOGIC.value
                confidence = 0.6
            structural_indicators.append("complex business logic")
        
        reasoning = "; ".join(structural_indicators) if structural_indicators else "Basic structural analysis"
        
        return {
            "category": category,
            "confidence": confidence,
            "reasoning": reasoning,
            "method": "structural_analysis",
            "structural_features": {
                "line_count": line_count,
                "has_return_value": has_return_value,
                "has_state_change": has_state_change,
                "has_control_flow": has_control_flow,
                "has_async_operations": has_async_operations,
                "has_error_handling": has_error_handling
            }
        }
    
    def _synthesize_expert_opinion(
        self, 
        analysis_results: Dict[str, Dict[str, Any]], 
        used_methods: List[str],
        start_time: float
    ) -> TaxonomyResult:
        """Synthesize multiple analysis results into expert opinion."""
        
        if not analysis_results:
            return TaxonomyResult(
                primary_category=FunctionCategory.UNKNOWN.value,
                confidence=0.0,
                alternative_categories=[],
                analysis_methods=used_methods,
                reasoning="No analysis methods succeeded",
                metadata={},
                processing_time=asyncio.get_event_loop().time() - start_time
            )
        
        # Expert opinion synthesis
        category_opinions = {}
        total_expert_weight = 0
        reasoning_parts = []
        metadata = {}
        
        for method, result in analysis_results.items():
            category = result["category"]
            confidence = result["confidence"]
            reasoning = result["reasoning"]
            
            # Expert weighting of different methods
            expert_weight = self._get_expert_weight(method)
            weighted_confidence = confidence * expert_weight
            
            if category not in category_opinions:
                category_opinions[category] = []
            
            category_opinions[category].append(weighted_confidence)
            total_expert_weight += expert_weight
            
            reasoning_parts.append(f"{method}: {reasoning}")
            metadata[f"expert_{method}"] = result
        
        # Calculate expert consensus
        category_consensus = {}
        for category, opinions in category_opinions.items():
            category_consensus[category] = sum(opinions) / len(opinions)
        
        # Rank by expert consensus
        ranked_categories = sorted(
            category_consensus.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        # Expert final opinion
        primary_category = ranked_categories[0][0]
        primary_confidence = ranked_categories[0][1]
        
        alternative_categories = [
            (cat, score) for cat, score in ranked_categories[1:self.max_alternatives + 1]
        ]
        
        # Expert reasoning
        expert_reasoning = " | ".join(reasoning_parts)
        
        processing_time = asyncio.get_event_loop().time() - start_time
        
        return TaxonomyResult(
            primary_category=primary_category,
            confidence=primary_confidence,
            alternative_categories=alternative_categories,
            analysis_methods=used_methods,
            reasoning=expert_reasoning,
            metadata=metadata,
            processing_time=processing_time
        )
    
    def _get_expert_weight(self, method: str) -> float:
        """Get expert weighting for different analysis methods."""
        expert_weights = {
            "pattern_matching": 1.0,
            "ai_classification": 1.2,  # AI gets slight preference
            "structural_analysis": 0.8,
            "intent_recognition": 0.9
        }
        return expert_weights.get(method, 1.0)
    
    async def analyze_function_collection(
        self, 
        functions: List[Tuple[str, str]], 
        analysis_methods: List[AnalysisMethod] = None
    ) -> List[TaxonomyResult]:
        """Analyze a collection of functions for comprehensive taxonomy."""
        
        self.logger.info(f"Starting analysis of {len(functions)} functions")
        results = []
        
        # Initialize progress manager with 10 second interval
        progress_manager = ProgressManager(interval_seconds=10.0)
        progress_manager.start(len(functions))
        
        for i, (function_code, function_name) in enumerate(functions):
            # Update progress (will only display if 10+ seconds have passed)
            progress_manager.update(i + 1, function_name)
            
            self.logger.info(f"Analyzing function {i+1}/{len(functions)}: {function_name}")
            start_time = asyncio.get_event_loop().time()
            
            result = await self.classify_function_purpose(function_code, function_name, analysis_methods)
            
            elapsed = asyncio.get_event_loop().time() - start_time
            self.logger.info(f"Function {function_name} analyzed in {elapsed:.2f}s")
            results.append(result)
        
        # Ensure final progress is shown
        progress_manager.finish()
        
        return results
    
    def get_expert_insights(self) -> Dict[str, Any]:
        """Get insights from the expert's classification experience."""
        
        if not self.classification_history:
            return {"message": "No classifications performed yet"}
        
        total_classifications = len(self.classification_history)
        
        # Method effectiveness analysis
        method_effectiveness = {}
        for result in self.classification_history:
            for method in result.analysis_methods:
                method_effectiveness[method] = method_effectiveness.get(method, 0) + 1
        
        # Confidence trends
        method_confidence = {}
        for method in method_effectiveness.keys():
            confidences = [
                result.confidence for result in self.classification_history
                if method in result.analysis_methods
            ]
            method_confidence[method] = sum(confidences) / len(confidences)
        
        # Domain insights
        category_insights = {}
        for result in self.classification_history:
            cat = result.primary_category
            category_insights[cat] = category_insights.get(cat, 0) + 1
        
        return {
            "expert_experience": {
                "total_classifications": total_classifications,
                "method_effectiveness": method_effectiveness,
                "method_confidence": method_confidence,
                "domain_coverage": category_insights
            },
            "performance_metrics": {
                "average_processing_time": sum(r.processing_time for r in self.classification_history) / total_classifications,
                "high_confidence_rate": len([r for r in self.classification_history if r.confidence > 0.8]) / total_classifications
            }
        }


async def demo_taxonomy_expert():
    """Demo the function taxonomy expert."""
    print("🧠 Function Taxonomy Expert Demo")
    print("=" * 40)
    
    expert = FunctionTaxonomyExpert(enable_ai=True)
    
    test_functions = [
        ("def get_user_name(self): return self._name", "get_user_name"),
        ("def set_config_value(self, key, val): self.config[key] = val", "set_config_value"),
        ("async def fetch_user_data(): return await api.get('/users')", "fetch_user_data"),
        ("def process_payment(transaction): return validate_and_charge(transaction)", "process_payment"),
        ("def validate_email_format(email): return '@' in email and '.' in email", "validate_email_format")
    ]
    
    for func_code, func_name in test_functions:
        print(f"\n📝 Function: {func_name}")
        print(f"Code: {func_code}")
        
        result = await expert.classify_function_purpose(func_code, func_name)
        
        print(f"🎯 Primary Classification: {result.primary_category} (confidence: {result.confidence:.2f})")
        if result.alternative_categories:
            print("📊 Alternative Classifications:")
            for cat, conf in result.alternative_categories:
                print(f"   - {cat}: {conf:.2f}")
        
        print(f"🔬 Analysis Methods: {', '.join(result.analysis_methods)}")
        print(f"⏱️ Processing Time: {result.processing_time:.3f}s")
    
    # Expert insights
    print(f"\n🧠 Expert Insights:")
    insights = expert.get_expert_insights()
    for category, data in insights.items():
        print(f"  {category}: {data}")


if __name__ == "__main__":
    asyncio.run(demo_taxonomy_expert())