#!/usr/bin/env python3
"""Test script to verify refactoring changes."""

try:
    # Test import of refactored detector
    from .ast_simhash_detector_refactored import ASTSimHashDetectorRefactored
    print("✓ Successfully imported ASTSimHashDetectorRefactored")
    
    # Test import of new detectors module
    from .detectors import (
        SimilarityDetector, SimilarityGraphBuilder, DetectorCacheManager,
        AdaptiveThresholdFinder, StatisticsCollector, TopPercentDuplicateFinder
    )
    print("✓ Successfully imported all detector components")
    
    # Test basic instantiation
    detector = ASTSimHashDetectorRefactored()
    print("✓ Successfully instantiated ASTSimHashDetectorRefactored")
    
    # Verify components are initialized
    assert hasattr(detector, 'similarity_detector')
    assert hasattr(detector, 'graph_builder')
    assert hasattr(detector, 'cache_manager')
    assert hasattr(detector, 'adaptive_threshold_finder')
    assert hasattr(detector, 'statistics_collector')
    assert hasattr(detector, 'top_percent_finder')
    print("✓ All components properly initialized")
    
    # Test component types
    assert isinstance(detector.similarity_detector, SimilarityDetector)
    assert isinstance(detector.graph_builder, SimilarityGraphBuilder)
    assert isinstance(detector.cache_manager, DetectorCacheManager)
    assert isinstance(detector.adaptive_threshold_finder, AdaptiveThresholdFinder)
    assert isinstance(detector.statistics_collector, StatisticsCollector)
    assert isinstance(detector.top_percent_finder, TopPercentDuplicateFinder)
    print("✓ All components have correct types")
    
    print("\n✅ All refactoring tests passed!")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    import traceback
    traceback.print_exc()
except AssertionError as e:
    print(f"❌ Assertion error: {e}")
    import traceback
    traceback.print_exc()
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    import traceback
    traceback.print_exc()

if __name__ == "__main__":
    print("Running refactoring tests...")