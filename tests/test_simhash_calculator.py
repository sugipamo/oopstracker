"""Test cases for SimHash calculator following TDD principles."""

import pytest
from oopstracker.core.simhash.calculator import SimHashCalculator


class TestSimHashCalculator:
    """Test cases for SimHashCalculator class."""

    def test_init_with_default_hash_size(self):
        """Test calculator initialization with default hash size."""
        calculator = SimHashCalculator()
        assert calculator.hash_size == 64

    def test_init_with_custom_hash_size(self):
        """Test calculator initialization with custom hash size."""
        calculator = SimHashCalculator(hash_size=128)
        assert calculator.hash_size == 128

    def test_calculate_hash_empty_string(self):
        """Test hash calculation for empty string."""
        calculator = SimHashCalculator()
        hash_value = calculator.calculate("", weights=[])
        assert isinstance(hash_value, int)
        assert 0 <= hash_value < 2**64

    def test_calculate_hash_simple_features(self):
        """Test hash calculation with simple features."""
        calculator = SimHashCalculator()
        features = ["hello", "world", "test"]
        weights = [1, 1, 1]
        hash_value = calculator.calculate(features, weights)
        assert isinstance(hash_value, int)
        assert 0 <= hash_value < 2**64

    def test_calculate_hash_weighted_features(self):
        """Test hash calculation with weighted features."""
        calculator = SimHashCalculator()
        features = ["important", "normal", "less"]
        weights = [3, 2, 1]
        hash_value = calculator.calculate(features, weights)
        assert isinstance(hash_value, int)
        assert 0 <= hash_value < 2**64

    def test_hash_consistency(self):
        """Test that same features produce same hash."""
        calculator = SimHashCalculator()
        features = ["feature1", "feature2", "feature3"]
        weights = [1, 2, 3]
        
        hash1 = calculator.calculate(features, weights)
        hash2 = calculator.calculate(features, weights)
        
        assert hash1 == hash2

    def test_hash_sensitivity_to_order(self):
        """Test that feature order affects hash value."""
        calculator = SimHashCalculator()
        features1 = ["a", "b", "c"]
        features2 = ["c", "b", "a"]
        weights = [1, 1, 1]
        
        hash1 = calculator.calculate(features1, weights)
        hash2 = calculator.calculate(features2, weights)
        
        # SimHash should be order-sensitive
        assert hash1 != hash2

    def test_hash_sensitivity_to_weights(self):
        """Test that weights affect hash value."""
        calculator = SimHashCalculator()
        features = ["feature1", "feature2"]
        
        hash1 = calculator.calculate(features, [1, 1])
        hash2 = calculator.calculate(features, [2, 1])
        
        assert hash1 != hash2

    def test_hamming_distance_identical(self):
        """Test Hamming distance for identical hashes."""
        calculator = SimHashCalculator()
        hash1 = calculator.calculate(["test"], [1])
        distance = calculator.hamming_distance(hash1, hash1)
        assert distance == 0

    def test_hamming_distance_different(self):
        """Test Hamming distance for different hashes."""
        calculator = SimHashCalculator()
        hash1 = calculator.calculate(["test1"], [1])
        hash2 = calculator.calculate(["test2"], [1])
        distance = calculator.hamming_distance(hash1, hash2)
        assert distance > 0
        assert distance <= 64  # Maximum possible distance

    def test_similarity_identical(self):
        """Test similarity score for identical content."""
        calculator = SimHashCalculator()
        hash1 = calculator.calculate(["content"], [1])
        similarity = calculator.similarity(hash1, hash1)
        assert similarity == 1.0

    def test_similarity_different(self):
        """Test similarity score for different content."""
        calculator = SimHashCalculator()
        hash1 = calculator.calculate(["content1"], [1])
        hash2 = calculator.calculate(["content2"], [1])
        similarity = calculator.similarity(hash1, hash2)
        assert 0.0 <= similarity <= 1.0
        assert similarity < 1.0

    def test_invalid_hash_size(self):
        """Test that invalid hash size raises error."""
        with pytest.raises(ValueError):
            SimHashCalculator(hash_size=0)
        
        with pytest.raises(ValueError):
            SimHashCalculator(hash_size=-1)

    def test_mismatched_features_weights(self):
        """Test that mismatched features and weights raise error."""
        calculator = SimHashCalculator()
        features = ["a", "b", "c"]
        weights = [1, 2]  # Too few weights
        
        with pytest.raises(ValueError):
            calculator.calculate(features, weights)

    def test_empty_features_list(self):
        """Test hash calculation with empty features list."""
        calculator = SimHashCalculator()
        hash_value = calculator.calculate([], [])
        assert isinstance(hash_value, int)
        # Empty features should produce a consistent hash
        assert hash_value == calculator.calculate([], [])