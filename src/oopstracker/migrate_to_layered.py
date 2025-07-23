"""
Migration helper to transition from ASTSimHashDetectorRefactored to ASTSimHashDetectorLayered.
"""

import logging
from .ast_simhash_detector_refactored import ASTSimHashDetectorRefactored
from .ast_simhash_detector_layered import ASTSimHashDetectorLayered

logger = logging.getLogger(__name__)


def migrate_detector(old_detector: ASTSimHashDetectorRefactored) -> ASTSimHashDetectorLayered:
    """
    Migrate from old detector to new layered detector.
    
    Args:
        old_detector: Instance of ASTSimHashDetectorRefactored
        
    Returns:
        New instance of ASTSimHashDetectorLayered with same data
    """
    logger.info("Starting migration to layered detector")
    
    # Create new detector with same configuration
    new_detector = ASTSimHashDetectorLayered(
        hamming_threshold=old_detector.hamming_threshold,
        db_path=old_detector.db_manager.db_path,
        include_tests=old_detector.trivial_filter.include_tests
    )
    
    # Data is already in the database, so it should be loaded automatically
    logger.info("Migration complete - data preserved in database")
    
    return new_detector


# Alias for backward compatibility
ASTSimHashDetector = ASTSimHashDetectorLayered


def create_detector(hamming_threshold: int = 10, 
                    db_path: str = "oopstracker_ast.db",
                    include_tests: bool = False,
                    use_layered: bool = True):
    """
    Factory function to create appropriate detector.
    
    Args:
        hamming_threshold: Maximum Hamming distance
        db_path: Database path
        include_tests: Include test functions
        use_layered: Use new layered architecture (default: True)
        
    Returns:
        Detector instance
    """
    if use_layered:
        logger.info("Creating layered AST SimHash detector")
        return ASTSimHashDetectorLayered(hamming_threshold, db_path, include_tests)
    else:
        logger.info("Creating legacy AST SimHash detector")
        return ASTSimHashDetectorRefactored(hamming_threshold, db_path, include_tests)