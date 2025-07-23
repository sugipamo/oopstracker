"""
Similarity Calculator Module
Calculates structural similarity between code units.
"""

import hashlib
from collections import Counter
from typing import List

from .code_unit import CodeUnit


class SimilarityCalculator:
    """
    Calculates various similarity metrics between code units.
    """
    
    def calculate_structural_similarity(self, unit1: CodeUnit, unit2: CodeUnit) -> float:
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
    
    def generate_ast_simhash(self, code_unit: CodeUnit) -> int:
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
        
        return self._simhash_from_features(features)
    
    def _simhash_from_features(self, features: List[str]) -> int:
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
    
    def hamming_distance(self, hash1: int, hash2: int) -> int:
        """
        Calculate Hamming distance between two SimHash values.
        
        Args:
            hash1: First SimHash value
            hash2: Second SimHash value
            
        Returns:
            Hamming distance (number of differing bits)
        """
        xor = hash1 ^ hash2
        distance = 0
        while xor:
            distance += xor & 1
            xor >>= 1
        return distance
    
    def simhash_similarity(self, hash1: int, hash2: int) -> float:
        """
        Calculate similarity score from SimHash values.
        
        Args:
            hash1: First SimHash value
            hash2: Second SimHash value
            
        Returns:
            Similarity score (0.0 to 1.0)
        """
        distance = self.hamming_distance(hash1, hash2)
        # Convert distance to similarity (64 is max distance for 64-bit hash)
        return 1.0 - (distance / 64.0)