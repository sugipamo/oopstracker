"""
Similarity calculation for code units.
"""

import hashlib
from typing import List, Tuple
from collections import Counter

from .code_unit import CodeUnit


class SimilarityCalculator:
    """Calculate similarity between code units."""
    
    @staticmethod
    def calculate_structural_similarity(unit1: CodeUnit, unit2: CodeUnit) -> float:
        """
        Calculate structural similarity between two code units using Bag of Words.
        
        Args:
            unit1: First code unit
            unit2: Second code unit
            
        Returns:
            Similarity score (0.0 to 1.0)
        """
        if not unit1.ast_structure or not unit2.ast_structure:
            return 0.0
        
        # Split structure signatures into tokens and count occurrences
        tokens1 = Counter(unit1.ast_structure.split('|'))
        tokens2 = Counter(unit2.ast_structure.split('|'))
        
        # Calculate cosine similarity with frequency
        intersection = sum((tokens1 & tokens2).values())
        magnitude1 = sum(v * v for v in tokens1.values()) ** 0.5
        magnitude2 = sum(v * v for v in tokens2.values()) ** 0.5
        
        if magnitude1 * magnitude2 == 0:
            return 0.0
        
        return intersection / (magnitude1 * magnitude2)
    
    @staticmethod
    def find_similar_units(target_unit: CodeUnit, candidate_units: List[CodeUnit], 
                          threshold: float = 0.7) -> List[Tuple[CodeUnit, float]]:
        """
        Find similar code units based on structural similarity.
        
        Args:
            target_unit: Target code unit to find similarities for
            candidate_units: List of candidate units to compare against
            threshold: Minimum similarity threshold
            
        Returns:
            List of (unit, similarity_score) tuples
        """
        similar_units = []
        
        for candidate in candidate_units:
            if candidate.name == target_unit.name and candidate.file_path == target_unit.file_path:
                continue  # Skip self
            
            similarity = SimilarityCalculator.calculate_structural_similarity(target_unit, candidate)
            
            if similarity >= threshold:
                similar_units.append((candidate, similarity))
        
        # Sort by similarity score (descending)
        similar_units.sort(key=lambda x: x[1], reverse=True)
        
        return similar_units
    
    @staticmethod
    def generate_ast_simhash(code_unit: CodeUnit) -> int:
        """
        Generate SimHash based on AST structure.
        
        Args:
            code_unit: Code unit to generate hash for
            
        Returns:
            64-bit SimHash value
        """
        if not code_unit.ast_structure:
            return 0
        
        # Use AST structure for SimHash generation
        structure_text = code_unit.ast_structure
        
        # Create weighted features
        features = []
        for token in structure_text.split('|'):
            if token.strip():
                features.append(token.strip())
        
        return SimilarityCalculator._simhash_from_features(features)
    
    @staticmethod
    def _simhash_from_features(features: List[str]) -> int:
        """
        Generate SimHash from a list of features.
        
        Args:
            features: List of feature strings
            
        Returns:
            64-bit SimHash value
        """
        # Initialize vector
        vector = [0] * 64
        
        for feature in features:
            # Get hash for this feature
            hash_value = int(hashlib.md5(feature.encode()).hexdigest(), 16)
            
            # Update vector based on hash bits
            for i in range(64):
                if hash_value & (1 << i):
                    vector[i] += 1
                else:
                    vector[i] -= 1
        
        # Convert to final hash
        simhash = 0
        for i in range(64):
            if vector[i] > 0:
                simhash |= (1 << i)
        
        return simhash