"""
Similarity calculation for code units based on AST features.
"""

import hashlib
from typing import List, Tuple
from collections import Counter

from .models import CodeUnit


class SimilarityCalculator:
    """Calculates similarity between code units using various metrics."""
    
    def calculate_structural_similarity(self, unit1: CodeUnit, unit2: CodeUnit) -> float:
        """
        Calculate structural similarity between two code units.
        Returns a score between 0 and 1.
        """
        if not unit1.ast_features or not unit2.ast_features:
            return 0.0
            
        # Compare structure tokens
        tokens1 = set(unit1.ast_features.structure_tokens)
        tokens2 = set(unit2.ast_features.structure_tokens)
        
        if not tokens1 and not tokens2:
            return 1.0
        if not tokens1 or not tokens2:
            return 0.0
            
        intersection = tokens1 & tokens2
        union = tokens1 | tokens2
        
        jaccard = len(intersection) / len(union) if union else 0
        
        # Compare complexity
        complexity_diff = abs(unit1.ast_features.complexity_score - unit2.ast_features.complexity_score)
        complexity_similarity = 1 / (1 + complexity_diff * 0.1)
        
        # Compare control flow patterns
        flow1 = set(unit1.ast_features.control_flow_patterns)
        flow2 = set(unit2.ast_features.control_flow_patterns)
        
        flow_similarity = 0.0
        if flow1 or flow2:
            flow_intersection = flow1 & flow2
            flow_union = flow1 | flow2
            flow_similarity = len(flow_intersection) / len(flow_union) if flow_union else 0
        
        # Weighted average
        similarity = (
            0.5 * jaccard +
            0.2 * complexity_similarity +
            0.3 * flow_similarity
        )
        
        return min(1.0, max(0.0, similarity))
    
    def find_similar_units(self, target_unit: CodeUnit, candidate_units: List[CodeUnit], 
                         threshold: float = 0.8) -> List[Tuple[CodeUnit, float]]:
        """
        Find units similar to target unit.
        Returns list of (unit, similarity_score) tuples.
        """
        similar_units = []
        
        for candidate in candidate_units:
            if candidate == target_unit:
                continue
                
            similarity = self.calculate_structural_similarity(target_unit, candidate)
            
            if similarity >= threshold:
                similar_units.append((candidate, similarity))
        
        # Sort by similarity descending
        similar_units.sort(key=lambda x: x[1], reverse=True)
        
        return similar_units
    
    def generate_ast_simhash(self, code_unit: CodeUnit) -> int:
        """
        Generate SimHash from AST features for fast similarity detection.
        """
        if not code_unit.ast_features:
            return 0
            
        # Combine all features
        features = []
        features.extend(code_unit.ast_features.structure_tokens)
        features.extend(code_unit.ast_features.control_flow_patterns)
        features.extend([f"DEP:{dep}" for dep in code_unit.ast_features.dependencies])
        features.extend([f"CALL:{call}" for call in code_unit.ast_features.function_calls])
        
        return self._simhash_from_features(features)
    
    def _simhash_from_features(self, features: List[str]) -> int:
        """
        Generate SimHash from feature list.
        """
        if not features:
            return 0
            
        # Initialize bit vector
        v = [0] * 64
        
        for feature in features:
            # Hash the feature
            h = int(hashlib.md5(feature.encode()).hexdigest(), 16)
            
            # Update bit vector
            for i in range(64):
                if h & (1 << i):
                    v[i] += 1
                else:
                    v[i] -= 1
        
        # Generate final hash
        simhash = 0
        for i in range(64):
            if v[i] > 0:
                simhash |= (1 << i)
                
        return simhash
    
    def hamming_distance(self, hash1: int, hash2: int) -> int:
        """Calculate Hamming distance between two hashes."""
        xor = hash1 ^ hash2
        distance = 0
        while xor:
            distance += xor & 1
            xor >>= 1
        return distance