"""
Complete function mapping system that integrates akinator classifier with oopstracker.
"""

import asyncio
import logging
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
import random

from .akinator_classifier import AkinatorClassifier, LLMEvaluation
from .semantic_detector import SemanticAwareDuplicateDetector


@dataclass
class FunctionMappingResult:
    """Result of complete function mapping process."""
    total_functions: int
    classified_functions: int
    learning_iterations: int
    accuracy_improvement: float
    final_categories: Dict[str, int]
    learned_rules: List[str]


class FunctionSelectionStrategy:
    """Strategies for selecting functions to classify and learn from."""
    
    @staticmethod
    def uncertainty_sampling(classifications: List[Tuple[str, float]]) -> List[int]:
        """Select functions with lowest confidence scores (uncertainty sampling)."""
        sorted_by_confidence = sorted(enumerate(classifications), key=lambda x: x[1][1])
        return [idx for idx, _ in sorted_by_confidence[:5]]  # Top 5 uncertain
    
    @staticmethod
    def random_sampling(classifications: List[Tuple[str, float]], count: int = 5) -> List[int]:
        """Random selection for baseline comparison."""
        return random.sample(range(len(classifications)), min(count, len(classifications)))
    
    @staticmethod
    def diversity_sampling(functions: List[str], count: int = 5) -> List[int]:
        """Select diverse functions based on code patterns."""
        # Simple diversity based on function length and complexity
        function_features = []
        for func in functions:
            lines = len(func.split('\n'))
            complexity = func.count('if') + func.count('for') + func.count('while') + func.count('try')
            function_features.append((lines, complexity))
        
        # K-means-like selection for diversity
        selected_indices = []
        while len(selected_indices) < min(count, len(functions)):
            # Find most different function from already selected
            best_idx = 0
            best_distance = -1
            
            for i, feature in enumerate(function_features):
                if i in selected_indices:
                    continue
                    
                min_distance = float('inf')
                for selected_idx in selected_indices:
                    distance = abs(feature[0] - function_features[selected_idx][0]) + \
                              abs(feature[1] - function_features[selected_idx][1])
                    min_distance = min(min_distance, distance)
                
                if len(selected_indices) == 0 or min_distance > best_distance:
                    best_distance = min_distance
                    best_idx = i
            
            selected_indices.append(best_idx)
        
        return selected_indices


class CompleteFunctionMapper:
    """Complete function mapping system with active learning."""
    
    def __init__(self, selection_strategy: str = "uncertainty"):
        self.classifier = AkinatorClassifier()
        self.detector = None
        self.logger = logging.getLogger(__name__)
        
        # Selection strategy
        if selection_strategy == "uncertainty":
            self.selection_strategy = FunctionSelectionStrategy.uncertainty_sampling
        elif selection_strategy == "random":
            self.selection_strategy = FunctionSelectionStrategy.random_sampling
        elif selection_strategy == "diversity":
            self.selection_strategy = FunctionSelectionStrategy.diversity_sampling
        else:
            self.selection_strategy = FunctionSelectionStrategy.uncertainty_sampling
    
    async def initialize(self):
        """Initialize the function mapper."""
        self.detector = SemanticAwareDuplicateDetector()
        await self.detector.initialize()
        self.logger.info("Function mapper initialized")
    
    async def cleanup(self):
        """Cleanup resources."""
        if self.detector:
            await self.detector.cleanup()
    
    async def map_all_functions(self, max_iterations: int = 10, target_accuracy: float = 0.85) -> FunctionMappingResult:
        """Map all functions in the project with active learning."""
        
        # Get all functions from the project
        function_units = [unit for unit in self.detector.structural_detector.code_units.values() 
                         if unit.type == 'function']
        
        if not function_units:
            self.logger.warning("No functions found in project")
            return FunctionMappingResult(0, 0, 0, 0.0, {}, [])
        
        self.logger.info(f"Found {len(function_units)} functions to classify")
        
        # Initial classification of all functions
        initial_results = []
        for unit in function_units:
            classification = self.classifier.classify_function(unit.source_code, unit.name)
            initial_results.append((unit, classification))
        
        # Calculate initial accuracy (using validation set)
        initial_validation = await self.classifier.validate_and_optimize_rules()
        initial_accuracy = initial_validation["overall_accuracy"]
        
        self.logger.info(f"Initial classification accuracy: {initial_accuracy:.2%}")
        
        # Active learning loop
        iteration = 0
        learned_rules_count = len(self.classifier.rules)
        
        for iteration in range(max_iterations):
            self.logger.info(f"Learning iteration {iteration + 1}/{max_iterations}")
            
            # Select functions for learning based on uncertainty
            classifications_with_confidence = [
                (result[1].category, result[1].confidence) 
                for result in initial_results
            ]
            
            selected_indices = self.selection_strategy(classifications_with_confidence)
            
            # Learn from selected functions
            learning_count = 0
            for idx in selected_indices:
                unit, classification = initial_results[idx]
                
                # Simulate LLM evaluation for learning
                # In real implementation, this would use actual LLM
                mock_evaluation = await self._mock_llm_evaluation(unit, classification)
                
                if mock_evaluation and not mock_evaluation.is_correct:
                    await self.classifier._learn_from_feedback(
                        unit.source_code, classification, mock_evaluation
                    )
                    learning_count += 1
            
            self.logger.info(f"Learned from {learning_count} functions in iteration {iteration + 1}")
            
            # Re-validate after learning
            validation_results = await self.classifier.validate_and_optimize_rules()
            current_accuracy = validation_results["overall_accuracy"]
            
            self.logger.info(f"Accuracy after iteration {iteration + 1}: {current_accuracy:.2%}")
            
            # Check if target accuracy reached
            if current_accuracy >= target_accuracy:
                self.logger.info(f"Target accuracy {target_accuracy:.2%} reached!")
                break
        
        # Final classification of all functions
        final_results = []
        category_counts = {}
        
        for unit in function_units:
            classification = self.classifier.classify_function(unit.source_code, unit.name)
            final_results.append((unit, classification))
            
            category = classification.category
            category_counts[category] = category_counts.get(category, 0) + 1
        
        # Calculate improvement
        final_validation = await self.classifier.validate_and_optimize_rules()
        final_accuracy = final_validation["overall_accuracy"]
        accuracy_improvement = final_accuracy - initial_accuracy
        
        # Get learned rules
        current_rules_count = len(self.classifier.rules)
        learned_rules = [
            rule.rule_id for rule in self.classifier.rules[learned_rules_count:]
        ]
        
        return FunctionMappingResult(
            total_functions=len(function_units),
            classified_functions=len(final_results),
            learning_iterations=iteration + 1,
            accuracy_improvement=accuracy_improvement,
            final_categories=category_counts,
            learned_rules=learned_rules
        )
    
    async def _mock_llm_evaluation(self, unit, classification) -> Optional[LLMEvaluation]:
        """Mock LLM evaluation for demonstration (replace with real LLM in production)."""
        
        # Simple heuristic-based evaluation
        function_name = unit.name.lower()
        code = unit.source_code.lower()
        
        # Rules for mock evaluation
        if classification.category == "unknown":
            # Try to guess correct category
            if any(word in function_name for word in ['process', 'handle', 'execute']):
                return LLMEvaluation(
                    is_correct=False,
                    correct_category="business_logic",
                    suggested_pattern=None,
                    reasoning="Function appears to process business logic",
                    confidence=0.8
                )
            elif 'validate' in function_name or 'check' in function_name:
                return LLMEvaluation(
                    is_correct=False,
                    correct_category="validation",
                    suggested_pattern=None,
                    reasoning="Function appears to validate data",
                    confidence=0.8
                )
            elif 'convert' in function_name or 'transform' in function_name:
                return LLMEvaluation(
                    is_correct=False,
                    correct_category="conversion",
                    suggested_pattern=None,
                    reasoning="Function appears to convert data",
                    confidence=0.8
                )
        
        # Accept current classification if it seems reasonable
        return LLMEvaluation(
            is_correct=True,
            correct_category=None,
            suggested_pattern=None,
            reasoning="Classification appears correct",
            confidence=0.9
        )
    
    async def generate_mapping_report(self, result: FunctionMappingResult) -> str:
        """Generate a comprehensive mapping report."""
        
        report = f"""
# Function Mapping Report

## Summary
- **Total Functions Analyzed**: {result.total_functions}
- **Successfully Classified**: {result.classified_functions}
- **Learning Iterations**: {result.learning_iterations}
- **Accuracy Improvement**: {result.accuracy_improvement:+.2%}

## Category Distribution
"""
        
        for category, count in sorted(result.final_categories.items()):
            percentage = (count / result.total_functions) * 100
            report += f"- **{category}**: {count} functions ({percentage:.1f}%)\n"
        
        if result.learned_rules:
            report += f"\n## Learned Rules ({len(result.learned_rules)})\n"
            for rule_id in result.learned_rules:
                report += f"- {rule_id}\n"
        
        # Add rules summary
        rules_summary = self.classifier.get_rules_summary()
        report += f"\n## Total Classification Rules: {rules_summary['total_rules']}\n"
        
        for category, rules in rules_summary['categories'].items():
            report += f"\n### {category.title()} ({len(rules)} rules)\n"
            for rule in rules[:3]:  # Show first 3 rules
                report += f"- `{rule['pattern']}` - {rule['description']}\n"
            if len(rules) > 3:
                report += f"- ... and {len(rules) - 3} more\n"
        
        return report


async def demo_complete_mapping():
    """Demonstrate the complete function mapping system."""
    
    print("🗺️  Complete Function Mapping System Demo")
    print("=" * 50)
    
    mapper = CompleteFunctionMapper(selection_strategy="uncertainty")
    
    try:
        await mapper.initialize()
        
        # Run complete mapping
        result = await mapper.map_all_functions(max_iterations=3, target_accuracy=0.80)
        
        print(f"\n📊 Mapping Results:")
        print(f"  Functions analyzed: {result.total_functions}")
        print(f"  Successfully classified: {result.classified_functions}")
        print(f"  Learning iterations: {result.learning_iterations}")
        print(f"  Accuracy improvement: {result.accuracy_improvement:+.2%}")
        
        print(f"\n📈 Category Distribution:")
        for category, count in sorted(result.final_categories.items()):
            percentage = (count / result.total_functions) * 100
            print(f"  {category}: {count} ({percentage:.1f}%)")
        
        if result.learned_rules:
            print(f"\n🎓 Learned Rules:")
            for rule_id in result.learned_rules:
                print(f"  - {rule_id}")
        
        # Generate full report
        report = await mapper.generate_mapping_report(result)
        print(f"\n📝 Full Report Generated ({len(report)} chars)")
        
    finally:
        await mapper.cleanup()


if __name__ == "__main__":
    asyncio.run(demo_complete_mapping())