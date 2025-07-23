"""
Akinator-style function classifier with regex patterns and LLM evaluation.
"""

import re
import asyncio
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

try:
    from intent_unified.core.semantic_analyzer import SemanticAnalyzer
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False


@dataclass
class ClassificationRule:
    """A regex-based classification rule."""
    rule_id: str
    pattern: str
    category: str
    description: str
    confidence: float = 0.8
    examples: List[str] = None
    
    def __post_init__(self):
        if self.examples is None:
            self.examples = []


@dataclass
class ClassificationResult:
    """Result of function classification."""
    category: str
    confidence: float
    matched_rules: List[str]
    reasoning: str


@dataclass
class LLMEvaluation:
    """LLM evaluation of classification result.""" 
    is_correct: bool
    correct_category: Optional[str]
    suggested_pattern: Optional[str]
    reasoning: str
    confidence: float


class FunctionCategory(Enum):
    """Standard function categories."""
    GETTER = "getter"
    SETTER = "setter" 
    CONSTRUCTOR = "constructor"
    DESTRUCTOR = "destructor"
    UTILITY = "utility"
    BUSINESS_LOGIC = "business_logic"
    DATA_PROCESSING = "data_processing"
    VALIDATION = "validation"
    CONVERSION = "conversion"
    ASYNC_HANDLER = "async_handler"
    ERROR_HANDLER = "error_handler"
    TEST_FUNCTION = "test_function"
    DECORATOR = "decorator"
    UNKNOWN = "unknown"


class AkinatorClassifier:
    """Akinator-style function classifier with learning capabilities."""
    
    def __init__(self):
        self.rules: List[ClassificationRule] = []
        self.logger = logging.getLogger(__name__)
        self.llm_analyzer = None
        
        # Initialize with basic rules
        self._initialize_basic_rules()
        
        if LLM_AVAILABLE:
            try:
                self.llm_analyzer = SemanticAnalyzer()
                self.logger.info("LLM analyzer initialized for evaluation")
            except Exception as e:
                self.logger.warning(f"Failed to initialize LLM analyzer: {e}")
    
    def _initialize_basic_rules(self):
        """Initialize with basic classification rules."""
        from .classification_rules import get_default_rules
        
        rule_configs = get_default_rules()
        basic_rules = []
        
        for config in rule_configs:
            rule = ClassificationRule(
                rule_id=config["rule_id"],
                pattern=config["pattern"],
                category=config["category"],
                description=config["description"],
                confidence=config.get("confidence", 0.8),
                examples=config.get("examples", [])
            )
            basic_rules.append(rule)
        
        self.rules.extend(basic_rules)
        self.logger.info(f"Initialized {len(basic_rules)} basic classification rules")
    
    def classify_function(self, function_code: str, function_name: str = None) -> ClassificationResult:
        """Classify a function using akinator-style regex matching."""
        matched_rules = []
        max_confidence = 0.0
        best_category = FunctionCategory.UNKNOWN.value
        reasoning_parts = []
        
        # Apply all rules and find best matches
        for rule in self.rules:
            if re.search(rule.pattern, function_code, re.IGNORECASE):
                matched_rules.append(rule.rule_id)
                reasoning_parts.append(f"Matched {rule.description}")
                
                if rule.confidence > max_confidence:
                    max_confidence = rule.confidence
                    best_category = rule.category
        
        # Additional heuristics based on function content
        if not matched_rules:
            # Analyze function content for patterns
            if "return " in function_code and function_code.count("return") == 1:
                if len(function_code.split('\n')) <= 3:
                    best_category = FunctionCategory.GETTER.value
                    max_confidence = 0.6
                    reasoning_parts.append("Simple return statement suggests getter")
            
            if "self." in function_code and "=" in function_code:
                best_category = FunctionCategory.SETTER.value
                max_confidence = 0.6
                reasoning_parts.append("Assignment to self attribute suggests setter")
        
        reasoning = "; ".join(reasoning_parts) if reasoning_parts else "No clear pattern detected"
        
        return ClassificationResult(
            category=best_category,
            confidence=max_confidence,
            matched_rules=matched_rules,
            reasoning=reasoning
        )
    
    async def evaluate_with_llm(self, function_code: str, classification: ClassificationResult) -> Optional[LLMEvaluation]:
        """Evaluate classification result using LLM."""
        if not self.llm_analyzer:
            return None
        
        try:
            prompt = f"""
            Analyze this function and evaluate the classification:
            
            Function Code:
            ```python
            {function_code}
            ```
            
            Current Classification: {classification.category}
            Confidence: {classification.confidence}
            Reasoning: {classification.reasoning}
            
            Questions:
            1. Is this classification correct? (yes/no)
            2. If incorrect, what should the correct category be?
            3. What regex pattern would better identify this type of function?
            
            Respond in JSON format:
            {{
                "is_correct": true/false,
                "correct_category": "category_name or null",
                "suggested_pattern": "regex_pattern or null", 
                "reasoning": "explanation",
                "confidence": 0.0-1.0
            }}
            """
            
            response = await self.llm_analyzer.analyze_intent(prompt)
            
            # Parse LLM response (simplified)
            # In real implementation, would use proper JSON parsing
            is_correct = "true" in response.lower()
            
            return LLMEvaluation(
                is_correct=is_correct,
                correct_category=None if is_correct else "business_logic",  # Simplified
                suggested_pattern=None,
                reasoning=response[:100] + "..." if len(response) > 100 else response,
                confidence=0.8
            )
            
        except Exception as e:
            self.logger.error(f"LLM evaluation failed: {e}")
            return None
    
    def add_rule(self, rule: ClassificationRule) -> bool:
        """Add a new classification rule."""
        try:
            # Validate pattern
            re.compile(rule.pattern)
            
            # Check for duplicates
            for existing_rule in self.rules:
                if existing_rule.rule_id == rule.rule_id:
                    self.logger.warning(f"Rule {rule.rule_id} already exists, updating")
                    existing_rule.pattern = rule.pattern
                    existing_rule.category = rule.category
                    existing_rule.description = rule.description
                    existing_rule.confidence = rule.confidence
                    return True
            
            self.rules.append(rule)
            self.logger.info(f"Added new classification rule: {rule.rule_id}")
            return True
            
        except re.error as e:
            self.logger.error(f"Invalid regex pattern in rule {rule.rule_id}: {e}")
            return False
    
    async def classify_and_learn(self, function_code: str, function_name: str = None) -> Tuple[ClassificationResult, Optional[LLMEvaluation]]:
        """Classify function and learn from LLM feedback."""
        # Step 1: Classify with current rules
        classification = self.classify_function(function_code, function_name)
        
        # Step 2: Evaluate with LLM
        evaluation = await self.evaluate_with_llm(function_code, classification)
        
        # Step 3: Learn from feedback
        if evaluation and not evaluation.is_correct:
            await self._learn_from_feedback(function_code, classification, evaluation)
        
        return classification, evaluation
    
    async def _learn_from_feedback(self, function_code: str, classification: ClassificationResult, evaluation: LLMEvaluation):
        """Learn new rule from LLM feedback with improved pattern generation."""
        if not evaluation.correct_category:
            return
        
        function_lines = function_code.strip().split('\n')
        if not function_lines:
            return
            
        first_line = function_lines[0].strip()
        
        # Extract function signature
        import re
        func_match = re.search(r'def\s+(\w+)\s*\([^)]*\)', first_line)
        if not func_match:
            return
            
        func_name = func_match.group(1)
        
        # Generate smart patterns based on category and function characteristics
        new_patterns = self._generate_smart_patterns(func_name, function_code, evaluation.correct_category)
        
        for pattern_info in new_patterns:
            new_rule = ClassificationRule(
                rule_id=f"learned_{evaluation.correct_category}_{pattern_info['type']}_{len(self.rules)}",
                pattern=pattern_info['pattern'],
                category=evaluation.correct_category,
                description=pattern_info['description'],
                confidence=pattern_info['confidence'],
                examples=[first_line]
            )
            
            self.add_rule(new_rule)
            self.logger.info(f"Learned new rule: {new_rule.rule_id} - {new_rule.description}")
    
    def _generate_smart_patterns(self, func_name: str, function_code: str, category: str) -> List[Dict[str, Any]]:
        """Generate intelligent patterns based on function analysis."""
        patterns = []
        
        # Analyze function name parts
        name_parts = func_name.split('_')
        first_part = name_parts[0] if name_parts else func_name
        last_part = name_parts[-1] if name_parts else func_name
        
        # Category-specific pattern generation
        if category == "business_logic":
            patterns.extend(self._generate_business_logic_patterns(func_name))
        elif category == "data_processing":
            patterns.extend(self._generate_data_processing_patterns(func_name))
        elif category == "validation":
            patterns.extend(self._generate_validation_patterns(func_name, function_code, last_part))
        
        # Generic pattern based on name structure
        if len(name_parts) > 1:
            patterns.append({
                'pattern': rf"def\s+{first_part}_\w+\s*\(",
                'type': 'name_prefix',
                'description': f"Function with '{first_part}_' prefix pattern",
                'confidence': 0.65
            })
        
        # If no specific patterns, create a basic one
        if not patterns:
            patterns.append({
                'pattern': rf"def\s+\w*{func_name}\w*\s*\(",
                'type': 'basic_name',
                'description': f"Basic pattern for {category} functions",
                'confidence': 0.6
            })
        
        return patterns
    
    def _generate_business_logic_patterns(self, func_name: str) -> List[Dict[str, Any]]:
        """Generate patterns for business logic functions."""
        from .classification_rules import get_pattern_keywords
        
        patterns = []
        keywords = get_pattern_keywords()
        action_words = keywords.get('business_logic', [])
        
        if any(word in func_name.lower() for word in action_words):
            pattern_words = "|".join(action_words)
            patterns.append({
                'pattern': rf"def\s+({pattern_words})_\w+\s*\(",
                'type': 'action_pattern',
                'description': f"Business logic function with action word pattern",
                'confidence': 0.75
            })
        return patterns
    
    def _generate_data_processing_patterns(self, func_name: str) -> List[Dict[str, Any]]:
        """Generate patterns for data processing functions."""
        from .classification_rules import get_pattern_keywords
        
        patterns = []
        keywords = get_pattern_keywords()
        data_words = keywords.get('data_processing', [])
        
        if any(word in func_name.lower() for word in data_words):
            pattern_words = "|".join(data_words)
            patterns.append({
                'pattern': rf"def\s+({pattern_words})\w*\s*\(",
                'type': 'data_pattern',
                'description': f"Data processing function pattern",
                'confidence': 0.8
            })
        return patterns
    
    def _generate_validation_patterns(self, func_name: str, function_code: str, last_part: str) -> List[Dict[str, Any]]:
        """Generate patterns for validation functions."""
        patterns = []
        if "return " in function_code and ("True" in function_code or "False" in function_code):
            patterns.append({
                'pattern': rf"def\s+.*{last_part}.*\s*\(",
                'type': 'validation_return',
                'description': f"Validation function with boolean return",
                'confidence': 0.7
            })
        return patterns
    
    async def validate_and_optimize_rules(self, test_functions: List[Tuple[str, str, str]] = None) -> Dict[str, Any]:
        """Validate existing rules and optimize them based on test data.
        
        Args:
            test_functions: List of (function_code, function_name, expected_category) tuples
        """
        if not test_functions:
            # Use default test cases
            test_functions = [
                ("def get_name(self): return self._name", "get_name", "getter"),
                ("def set_value(self, val): self.value = val", "set_value", "setter"),
                ("def process_data(data): return transform(data)", "process_data", "business_logic"),
                ("def validate_email(email): return '@' in email", "validate_email", "validation"),
                ("async def fetch_api(): return await get()", "fetch_api", "async_handler")
            ]
        
        validation_results = {
            "total_tests": len(test_functions),
            "correct_classifications": 0,
            "incorrect_classifications": 0,
            "rule_performance": {},
            "optimization_suggestions": []
        }
        
        # Test each function
        for func_code, func_name, expected_category in test_functions:
            classification = self.classify_function(func_code, func_name)
            
            is_correct = classification.category == expected_category
            if is_correct:
                validation_results["correct_classifications"] += 1
            else:
                validation_results["incorrect_classifications"] += 1
                
                # Generate optimization suggestion
                validation_results["optimization_suggestions"].append({
                    "function_name": func_name,
                    "expected": expected_category,
                    "actual": classification.category,
                    "confidence": classification.confidence,
                    "suggestion": f"Consider adding rule for {expected_category} pattern"
                })
        
        # Analyze rule performance
        for rule in self.rules:
            usage_count = 0
            correct_matches = 0
            
            for func_code, func_name, expected_category in test_functions:
                if re.search(rule.pattern, func_code, re.IGNORECASE):
                    usage_count += 1
                    if rule.category == expected_category:
                        correct_matches += 1
            
            if usage_count > 0:
                accuracy = correct_matches / usage_count
                validation_results["rule_performance"][rule.rule_id] = {
                    "usage_count": usage_count,
                    "accuracy": accuracy,
                    "category": rule.category,
                    "confidence": rule.confidence
                }
        
        validation_results["overall_accuracy"] = (
            validation_results["correct_classifications"] / validation_results["total_tests"]
        )
        
        return validation_results
    
    async def batch_classify_functions(self, functions: List[Tuple[str, str]]) -> List[Dict[str, Any]]:
        """Classify multiple functions in batch with learning."""
        results = []
        
        for func_code, func_name in functions:
            classification, evaluation = await self.classify_and_learn(func_code, func_name)
            
            results.append({
                "function_name": func_name,
                "code_preview": func_code[:100] + "..." if len(func_code) > 100 else func_code,
                "classification": classification.category,
                "confidence": classification.confidence,
                "reasoning": classification.reasoning,
                "matched_rules": classification.matched_rules,
                "llm_evaluation": {
                    "available": evaluation is not None,
                    "is_correct": evaluation.is_correct if evaluation else None,
                    "suggested_category": evaluation.correct_category if evaluation else None
                } if evaluation else None
            })
        
        return results
    
    def get_rules_summary(self) -> Dict[str, Any]:
        """Get summary of current classification rules."""
        categories = {}
        for rule in self.rules:
            if rule.category not in categories:
                categories[rule.category] = []
            categories[rule.category].append({
                "rule_id": rule.rule_id,
                "pattern": rule.pattern,
                "description": rule.description,
                "confidence": rule.confidence
            })
        
        return {
            "total_rules": len(self.rules),
            "categories": categories
        }
    
    def export_rules(self) -> List[Dict[str, Any]]:
        """Export all rules for persistence or analysis."""
        return [
            {
                "rule_id": rule.rule_id,
                "pattern": rule.pattern,
                "category": rule.category,
                "description": rule.description,
                "confidence": rule.confidence,
                "examples": rule.examples
            }
            for rule in self.rules
        ]
    
    def import_rules(self, rules_data: List[Dict[str, Any]]) -> int:
        """Import rules from external source."""
        imported_count = 0
        
        for rule_data in rules_data:
            try:
                rule = ClassificationRule(
                    rule_id=rule_data["rule_id"],
                    pattern=rule_data["pattern"],
                    category=rule_data["category"],
                    description=rule_data["description"],
                    confidence=rule_data.get("confidence", 0.7),
                    examples=rule_data.get("examples", [])
                )
                
                if self.add_rule(rule):
                    imported_count += 1
                    
            except Exception as e:
                self.logger.error(f"Failed to import rule {rule_data.get('rule_id', 'unknown')}: {e}")
        
        return imported_count


async def demo_akinator_classifier():
    """Demo the akinator classifier functionality."""
    classifier = AkinatorClassifier()
    
    # Sample functions to test
    test_functions = [
        ("def get_name(self): return self._name", "get_name"),
        ("def set_value(self, val): self.value = val", "set_value"),
        ("def __init__(self, name): self.name = name", "__init__"),
        ("async def fetch_data(): return await api.get()", "fetch_data"),
        ("def test_login(): assert login('user', 'pass')", "test_login"),
        ("def calculate_tax(income): return income * 0.2", "calculate_tax")
    ]
    
    print("🎯 Akinator Function Classifier Demo")
    print("=" * 50)
    
    for func_code, func_name in test_functions:
        print(f"\n📝 Function: {func_name}")
        print(f"Code: {func_code}")
        
        # Classify and learn
        classification, evaluation = await classifier.classify_and_learn(func_code, func_name)
        
        print(f"✅ Classification: {classification.category} (confidence: {classification.confidence:.2f})")
        print(f"💭 Reasoning: {classification.reasoning}")
        
        if evaluation:
            print(f"🤖 LLM Evaluation: {'Correct' if evaluation.is_correct else 'Incorrect'}")
            if not evaluation.is_correct:
                print(f"🔄 Suggested: {evaluation.correct_category}")
    
    # Show learned rules
    print(f"\n📊 Rules Summary:")
    summary = classifier.get_rules_summary()
    print(f"Total rules: {summary['total_rules']}")
    for category, rules in summary['categories'].items():
        print(f"  {category}: {len(rules)} rules")


if __name__ == "__main__":
    asyncio.run(demo_akinator_classifier())