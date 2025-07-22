#!/usr/bin/env python3
"""
Dynamic Pattern Generator - Extract pattern to solve scaling issues.

This module applies the Extract and Promote refactor patterns to create
adaptive pattern generation for realistic function name splitting.
"""

import re
import logging
from typing import List, Dict, Any, Tuple, Optional
from collections import Counter, defaultdict


class DynamicPatternGenerator:
    """
    Generate splitting patterns dynamically based on actual function analysis.
    
    Applies Extract pattern to separate pattern generation logic from splitting,
    and Promote pattern to elevate static patterns to dynamic analysis.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def analyze_function_structure(self, functions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze the structure of function names to understand patterns.
        
        Args:
            functions: List of function dictionaries with 'name' and 'code' keys
            
        Returns:
            Analysis results with prefix, suffix, and pattern statistics
        """
        if not functions:
            return {'prefixes': {}, 'suffixes': {}, 'word_counts': {}, 'patterns': []}
        
        prefixes = Counter()
        suffixes = Counter()  
        word_counts = Counter()
        middle_patterns = Counter()
        
        for func in functions:
            name = func.get('name', '')
            if not name:
                continue
                
            # Split by underscore
            parts = name.split('_')
            word_counts[len(parts)] += 1
            
            if len(parts) >= 1:
                prefixes[parts[0]] += 1
            
            if len(parts) >= 2:
                suffixes[parts[-1]] += 1
            
            if len(parts) >= 3:
                # Middle pattern analysis
                middle = '_'.join(parts[1:-1]) if len(parts) > 2 else parts[1]
                middle_patterns[middle] += 1
        
        return {
            'prefixes': dict(prefixes.most_common(20)),
            'suffixes': dict(suffixes.most_common(20)), 
            'word_counts': dict(word_counts),
            'middle_patterns': dict(middle_patterns.most_common(15)),
            'total_functions': len(functions)
        }
    
    def generate_adaptive_patterns(self, functions: List[Dict[str, Any]], 
                                 target_split_ratio: float = 0.5) -> List[Tuple[str, str]]:
        """
        Generate regex patterns that will split functions close to target ratio.
        
        Args:
            functions: List of functions to analyze
            target_split_ratio: Target ratio for splitting (0.5 = 50/50 split)
            
        Returns:
            List of (pattern, reasoning) tuples
        """
        analysis = self.analyze_function_structure(functions)
        patterns = []
        
        if analysis['total_functions'] < 2:
            return patterns
        
        target_count = int(analysis['total_functions'] * target_split_ratio)
        
        # Strategy 1: Prefix-based splitting
        prefix_patterns = self._generate_prefix_patterns(analysis, target_count)
        patterns.extend(prefix_patterns)
        
        # Strategy 2: Suffix-based splitting  
        suffix_patterns = self._generate_suffix_patterns(analysis, target_count)
        patterns.extend(suffix_patterns)
        
        # Strategy 3: Word count-based splitting
        wordcount_patterns = self._generate_wordcount_patterns(analysis, target_count)
        patterns.extend(wordcount_patterns)
        
        # Strategy 4: Alphabetical splitting (fallback)
        if not patterns:
            alpha_pattern = self._generate_alphabetical_pattern(functions)
            if alpha_pattern:
                patterns.append(alpha_pattern)
        
        # Sort by estimated effectiveness
        patterns = self._rank_patterns_by_effectiveness(patterns, functions)
        
        return patterns[:3]  # Return top 3 patterns
    
    def _generate_prefix_patterns(self, analysis: Dict, target_count: int) -> List[Tuple[str, str]]:
        """Generate patterns based on function name prefixes."""
        patterns = []
        prefixes = analysis['prefixes']
        
        if not prefixes:
            return patterns
        
        # Find combinations of prefixes that approximate target count
        sorted_prefixes = sorted(prefixes.items(), key=lambda x: x[1], reverse=True)
        
        # Single prefix patterns
        for prefix, count in sorted_prefixes[:5]:
            if abs(count - target_count) < target_count * 0.3:  # Within 30% of target
                pattern = f"def\\s+{re.escape(prefix)}_"
                reasoning = f"Split {prefix}_* functions ({count} functions)"
                patterns.append((pattern, reasoning))
        
        # Combined prefix patterns
        cumulative_count = 0
        selected_prefixes = []
        for prefix, count in sorted_prefixes:
            if cumulative_count + count <= target_count * 1.2:  # Allow 20% overage
                selected_prefixes.append(prefix)
                cumulative_count += count
                
                if len(selected_prefixes) >= 2 and abs(cumulative_count - target_count) < target_count * 0.2:
                    prefix_group = '|'.join(re.escape(p) for p in selected_prefixes)
                    pattern = f"def\\s+({prefix_group})_"
                    reasoning = f"Group prefixes: {', '.join(selected_prefixes)} ({cumulative_count} functions)"
                    patterns.append((pattern, reasoning))
        
        return patterns
    
    def _generate_suffix_patterns(self, analysis: Dict, target_count: int) -> List[Tuple[str, str]]:
        """Generate patterns based on function name suffixes."""
        patterns = []
        suffixes = analysis['suffixes']
        
        if not suffixes:
            return patterns
        
        sorted_suffixes = sorted(suffixes.items(), key=lambda x: x[1], reverse=True)
        
        for suffix, count in sorted_suffixes[:3]:
            if abs(count - target_count) < target_count * 0.3:
                pattern = f"def\\s+\\w+_{re.escape(suffix)}\\s*\\("
                reasoning = f"Split *_{suffix} functions ({count} functions)"
                patterns.append((pattern, reasoning))
        
        return patterns
    
    def _generate_wordcount_patterns(self, analysis: Dict, target_count: int) -> List[Tuple[str, str]]:
        """Generate patterns based on word count in function names."""
        patterns = []
        word_counts = analysis['word_counts']
        
        if not word_counts:
            return patterns
        
        # Find word counts that give good splits
        for word_count, count in word_counts.items():
            if abs(count - target_count) < target_count * 0.3 and word_count > 1:
                if word_count == 2:
                    pattern = "def\\s+\\w+_\\w+\\s*\\("
                elif word_count == 3:
                    pattern = "def\\s+\\w+_\\w+_\\w+\\s*\\("
                elif word_count == 4:
                    pattern = "def\\s+\\w+_\\w+_\\w+_\\w+\\s*\\("
                else:
                    pattern = f"def\\s+(?:\\w+_){{{word_count}}}\\s*\\("
                
                reasoning = f"Functions with {word_count} words ({count} functions)"
                patterns.append((pattern, reasoning))
        
        return patterns
    
    def _generate_alphabetical_pattern(self, functions: List[Dict[str, Any]]) -> Optional[Tuple[str, str]]:
        """Generate alphabetical split pattern as fallback."""
        if not functions:
            return None
        
        # Split roughly in the middle of alphabet
        pattern = "def\\s+[a-m]"
        reasoning = "Alphabetical split (A-M vs N-Z)"
        return (pattern, reasoning)
    
    def _rank_patterns_by_effectiveness(self, patterns: List[Tuple[str, str]], 
                                      functions: List[Dict[str, Any]]) -> List[Tuple[str, str]]:
        """Rank patterns by how well they split the functions."""
        if not patterns or not functions:
            return patterns
        
        scored_patterns = []
        total_functions = len(functions)
        
        for pattern, reasoning in patterns:
            try:
                # Test pattern against functions
                matches = 0
                for func in functions:
                    test_code = f"def {func.get('name', '')}():"
                    if re.search(pattern, test_code):
                        matches += 1
                
                # Score based on how close to 50/50 split
                split_ratio = matches / total_functions if total_functions > 0 else 0
                ideal_distance = abs(split_ratio - 0.5)
                effectiveness_score = 1.0 - (ideal_distance * 2)  # Higher score = better split
                
                # Bonus for reasonable match counts (avoid 0 or 100% matches)
                if 0.1 <= split_ratio <= 0.9:
                    effectiveness_score += 0.2
                
                scored_patterns.append((effectiveness_score, (pattern, reasoning), matches))
                
            except re.error:
                # Invalid regex, score as 0
                scored_patterns.append((0.0, (pattern, reasoning), 0))
        
        # Sort by effectiveness score (descending)
        scored_patterns.sort(key=lambda x: x[0], reverse=True)
        
        # Log pattern effectiveness
        self.logger.info(f"Pattern effectiveness ranking:")
        for score, (pattern, reasoning), matches in scored_patterns[:3]:
            self.logger.info(f"  Score: {score:.2f}, Matches: {matches}/{total_functions}, Pattern: {pattern[:30]}...")
        
        return [pattern_tuple for _, pattern_tuple, _ in scored_patterns]
    
    def test_pattern_effectiveness(self, pattern: str, functions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Test how effectively a pattern splits the given functions.
        
        Args:
            pattern: Regex pattern to test
            functions: Functions to test against
            
        Returns:
            Dictionary with effectiveness metrics
        """
        if not functions:
            return {'matches': 0, 'total': 0, 'ratio': 0.0, 'effectiveness': 0.0}
        
        matches = 0
        for func in functions:
            test_code = f"def {func.get('name', '')}():"
            try:
                if re.search(pattern, test_code):
                    matches += 1
            except re.error:
                continue
        
        total = len(functions)
        ratio = matches / total if total > 0 else 0.0
        
        # Effectiveness is how close to 50/50 split (1.0 = perfect, 0.0 = worst)
        effectiveness = 1.0 - (abs(ratio - 0.5) * 2)
        
        return {
            'matches': matches,
            'total': total,
            'ratio': ratio,
            'effectiveness': effectiveness,
            'split_quality': 'Good' if 0.3 <= ratio <= 0.7 else 'Poor'
        }