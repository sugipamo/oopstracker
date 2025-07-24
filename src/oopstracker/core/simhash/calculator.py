"""
SimHash calculation for code similarity detection.
"""

import hashlib
from typing import List, Union


class SimHashCalculator:
    """
    Calculates SimHash values for code similarity detection.
    """
    
    def __init__(self, hash_size: int = 64):
        """
        Initialize SimHash calculator.
        
        Args:
            hash_size: Size of the hash in bits (default: 64)
        
        Raises:
            ValueError: If hash_size is not positive
        """
        if hash_size <= 0:
            raise ValueError(f"hash_size must be positive, got {hash_size}")
        self.hash_size = hash_size
    
    def calculate(self, features: Union[str, List[str]], weights: List[int] = None) -> int:
        """
        Calculate SimHash for given features.
        
        Args:
            features: String or list of feature strings
            weights: Optional weights for each feature
            
        Returns:
            SimHash value as integer
        """
        # Handle empty input
        if not features:
            return 0
        
        # Convert string to list if needed
        if isinstance(features, str):
            if not features:
                return 0
            features = [features]
        
        # Initialize weights if not provided
        if weights is None:
            weights = [1] * len(features)
        
        # Ensure weights match features length
        if len(weights) < len(features):
            weights.extend([1] * (len(features) - len(weights)))
        
        # Initialize bit vector
        bit_vector = [0] * self.hash_size
        
        # Process each feature
        for feature, weight in zip(features, weights):
            # Get hash of feature
            feature_hash = int(hashlib.md5(feature.encode()).hexdigest(), 16)
            
            # Update bit vector based on hash bits
            for i in range(self.hash_size):
                bit = (feature_hash >> i) & 1
                if bit == 1:
                    bit_vector[i] += weight
                else:
                    bit_vector[i] -= weight
        
        # Create final hash
        simhash = 0
        for i in range(self.hash_size):
            if bit_vector[i] > 0:
                simhash |= (1 << i)
        
        return simhash
    
    def hamming_distance(self, hash1: int, hash2: int) -> int:
        """
        Calculate Hamming distance between two hashes.
        
        Args:
            hash1: First hash value
            hash2: Second hash value
            
        Returns:
            Hamming distance
        """
        xor = hash1 ^ hash2
        distance = 0
        while xor:
            distance += xor & 1
            xor >>= 1
        return distance
    
    def calc_similarity(self, hash1: int, hash2: int) -> float:
        """
        Calculate similarity score between two hashes.
        
        Args:
            hash1: First hash value
            hash2: Second hash value
            
        Returns:
            Similarity score between 0 and 1 (1 = identical, 0 = completely different)
        """
        # Calculate Hamming distance
        distance = self.hamming_distance(hash1, hash2)
        
        # Normalize to 0-1 range
        normalized_distance = distance / self.hash_size
        
        # Convert distance to similarity (inverse relationship)
        similarity_score = 1.0 - normalized_distance
        
        return similarity_score
    
    def similarity(self, hash1: int, hash2: int) -> float:
        """Alias for calc_similarity for backward compatibility."""
        return self.calc_similarity(hash1, hash2)