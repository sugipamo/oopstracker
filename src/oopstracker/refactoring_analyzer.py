"""
Refactoring possibility analyzer for detected duplicates.
Analyzes duplicate code patterns and suggests appropriate refactoring strategies.
"""

import ast
import logging
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

from .ast_analyzer import CodeUnit


logger = logging.getLogger(__name__)


class RefactoringType(Enum):
    """Types of refactoring that can be applied."""
    EXTRACT_METHOD = "extract_method"
    EXTRACT_CLASS = "extract_class"
    EXTRACT_SUPERCLASS = "extract_superclass"
    TEMPLATE_METHOD = "template_method"
    STRATEGY_PATTERN = "strategy_pattern"
    INTENTIONAL_DUPLICATE = "intentional_duplicate"
    COMPLEX_REFACTORING = "complex_refactoring"


@dataclass
class RefactoringRecommendation:
    """Represents a refactoring recommendation."""
    refactoring_type: RefactoringType
    confidence: float  # 0.0 to 1.0
    description: str
    impact_score: float  # Estimated impact/benefit
    complexity: str  # "low", "medium", "high"
    affected_units: List[CodeUnit]
    

class RefactoringAnalyzer:
    """Analyzes duplicate code and suggests refactoring strategies."""
    
    def __init__(self):
        self.logger = logger
    
    def analyze_duplicates(self, duplicate_groups: List[List[CodeUnit]]) -> Dict[str, List[RefactoringRecommendation]]:
        """
        Analyze groups of duplicate code and recommend refactoring strategies.
        
        Args:
            duplicate_groups: Groups of duplicate code units
            
        Returns:
            Dictionary mapping group IDs to refactoring recommendations
        """
        recommendations = {}
        
        for i, group in enumerate(duplicate_groups):
            group_id = f"group_{i}"
            group_recommendations = self._analyze_group(group)
            if group_recommendations:
                recommendations[group_id] = group_recommendations
        
        return recommendations
    
    def _analyze_group(self, units: List[CodeUnit]) -> List[RefactoringRecommendation]:
        """Analyze a single group of duplicate units."""
        if len(units) < 2:
            return []
        
        recommendations = []
        
        # Check for simple method extraction
        if self._is_simple_extraction(units):
            recommendations.append(RefactoringRecommendation(
                refactoring_type=RefactoringType.EXTRACT_METHOD,
                confidence=0.9,
                description="Extract common logic into a shared method",
                impact_score=0.8,
                complexity="low",
                affected_units=units
            ))
        
        # Check for class extraction possibility
        if self._has_common_base_structure(units):
            recommendations.append(RefactoringRecommendation(
                refactoring_type=RefactoringType.EXTRACT_SUPERCLASS,
                confidence=0.7,
                description="Extract common structure into a base class",
                impact_score=0.7,
                complexity="medium",
                affected_units=units
            ))
        
        # Check for template method pattern
        if self._is_template_method_candidate(units):
            recommendations.append(RefactoringRecommendation(
                refactoring_type=RefactoringType.TEMPLATE_METHOD,
                confidence=0.8,
                description="Apply template method pattern for varying implementations",
                impact_score=0.75,
                complexity="medium",
                affected_units=units
            ))
        
        # Check if it's intentional duplication (e.g., test code)
        if self._is_intentional_duplicate(units):
            recommendations.append(RefactoringRecommendation(
                refactoring_type=RefactoringType.INTENTIONAL_DUPLICATE,
                confidence=0.85,
                description="Likely intentional duplication (test code or similar)",
                impact_score=0.1,
                complexity="none",
                affected_units=units
            ))
        
        # If no specific pattern matches, suggest complex refactoring
        if not recommendations:
            recommendations.append(RefactoringRecommendation(
                refactoring_type=RefactoringType.COMPLEX_REFACTORING,
                confidence=0.5,
                description="Complex refactoring needed - manual analysis recommended",
                impact_score=0.5,
                complexity="high",
                affected_units=units
            ))
        
        return recommendations
    
    def _is_simple_extraction(self, units: List) -> bool:
        """Check if units can be simply extracted into a method."""
        # All units should be functions
        unit_types = []
        for unit in units:
            if hasattr(unit, 'metadata') and unit.metadata:
                unit_type = unit.metadata.get('type', 'unknown')
            else:
                unit_type = 'unknown'
            unit_types.append(unit_type)
        
        if not all(t == 'function' for t in unit_types):
            return False
        
        # Check if they have similar structure (simplified check)
        return len(units) >= 2
    
    def _has_common_base_structure(self, units: List) -> bool:
        """Check if units share common base structure suitable for class extraction."""
        # Should have at least some class units
        class_units = []
        for unit in units:
            if hasattr(unit, 'metadata') and unit.metadata:
                unit_type = unit.metadata.get('type', 'unknown')
                if unit_type == 'class':
                    class_units.append(unit)
        
        if len(class_units) < 2:
            return False
        
        # Check for common methods/attributes (simplified check)
        return True
    
    def _is_template_method_candidate(self, units: List) -> bool:
        """Check if units follow a template method pattern."""
        # Look for similar structure with small variations
        if len(units) < 2:
            return False
        
        # Check if they're all functions
        unit_types = []
        for unit in units:
            if hasattr(unit, 'metadata') and unit.metadata:
                unit_type = unit.metadata.get('type', 'unknown')
            else:
                unit_type = 'unknown'
            unit_types.append(unit_type)
        
        if not all(t == 'function' for t in unit_types):
            return False
        
        # Simplified check - assume template method pattern if multiple functions
        return len(units) >= 2
    
    def _is_intentional_duplicate(self, units: List) -> bool:
        """Check if duplication is likely intentional (e.g., test code)."""
        # Check if files are test files
        test_indicators = ['test_', '_test', 'tests/', 'test/', 'spec_', '_spec']
        
        for unit in units:
            if hasattr(unit, 'file_path') and unit.file_path:
                file_path_lower = unit.file_path.lower()
                if any(indicator in file_path_lower for indicator in test_indicators):
                    return True
        
        # Check for test-like function names
        for unit in units:
            unit_name = getattr(unit, 'function_name', None) or getattr(unit, 'name', None)
            if unit_name and any(indicator in unit_name.lower() for indicator in ['test_', 'setup', 'teardown']):
                return True
        
        return False
    
    def calculate_refactoring_roi(self, recommendation: RefactoringRecommendation) -> float:
        """
        Calculate ROI (Return on Investment) for a refactoring recommendation.
        
        Returns:
            ROI score (0.0 to 1.0)
        """
        # Simple ROI calculation based on impact and complexity
        complexity_factor = {
            "none": 1.0,
            "low": 0.8,
            "medium": 0.5,
            "high": 0.2
        }.get(recommendation.complexity, 0.5)
        
        # Number of affected units increases ROI
        unit_factor = min(1.0, len(recommendation.affected_units) / 10)
        
        roi = recommendation.impact_score * complexity_factor * unit_factor * recommendation.confidence
        
        return min(1.0, roi)