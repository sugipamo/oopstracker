"""
Hybrid detection combining OOPStracker's SimHash with AST-based analysis.
"""

import sys
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass

# Add evocraft-ast-dedup to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "evocraft-ast-dedup" / "src"))

try:
    from evocraft_ast_dedup.deduplication_engine import DeduplicationEngine
    from evocraft_ast_dedup.models import DuplicationResult
    from evocraft_ast_dedup import presets
    HAS_AST_DEDUP = True
except ImportError as e:
    HAS_AST_DEDUP = False
    logging.warning(f"evocraft-ast-dedup not available: {e}")
    
    # Create dummy class for type hints when AST dedup is not available
    class DuplicationResult:
        def __init__(self):
            self.is_duplicate = False
            self.similarity_score = 0.0

from .core import CodeMemory
from .models import SimilarityResult, CodeRecord


@dataclass
class HybridResult:
    """Result from hybrid detection combining SimHash and AST analysis."""
    simhash_result: SimilarityResult
    ast_result: Optional[DuplicationResult] = None
    method_used: str = "simhash_only"
    confidence: float = 0.0
    performance_metrics: Dict[str, float] = None
    
    @property
    def is_duplicate(self) -> bool:
        """Combined duplicate detection result."""
        if self.ast_result is not None:
            return self.ast_result.is_duplicate
        return self.simhash_result.is_duplicate
    
    @property
    def similarity_score(self) -> float:
        """Combined similarity score."""
        if self.ast_result is not None:
            return self.ast_result.similarity_score
        return self.simhash_result.similarity_score
    
    @property
    def matched_records(self) -> List[CodeRecord]:
        """Combined matched records."""
        return self.simhash_result.matched_records


class HybridCodeMemory:
    """
    Hybrid code memory combining SimHash fast filtering with AST precision.
    
    This class provides a two-stage detection process:
    1. Fast SimHash filtering (O(log n))
    2. Precise AST analysis on candidates (when available)
    """
    
    def __init__(self, 
                 db_path: str = "oopstracker.db",
                 simhash_threshold: int = 12,
                 ast_threshold: float = 0.8,
                 enable_ast_analysis: bool = True):
        """
        Initialize hybrid detection system.
        
        Args:
            db_path: Database path for storage
            simhash_threshold: Hamming distance threshold for SimHash
            ast_threshold: Similarity threshold for AST analysis
            enable_ast_analysis: Whether to enable AST analysis (requires evocraft-ast-dedup)
        """
        self.logger = logging.getLogger(__name__)
        
        # Initialize SimHash detector
        self.simhash_memory = CodeMemory(db_path=db_path, threshold=simhash_threshold)
        
        # Initialize AST detector if available
        self.ast_engine = None
        self.enable_ast_analysis = enable_ast_analysis and HAS_AST_DEDUP
        
        if self.enable_ast_analysis:
            try:
                # Use same database path but different file for AST
                ast_db_path = db_path.replace('.db', '_ast.db')
                self.ast_engine = DeduplicationEngine(
                    db_path=ast_db_path,
                    strategy=presets.NORMAL,
                    verbose=False
                )
                self.logger.info("AST analysis enabled")
            except Exception as e:
                self.logger.warning(f"AST analysis disabled due to error: {e}")
                self.enable_ast_analysis = False
        else:
            self.logger.info("AST analysis disabled")
    
    def register(self, 
                 code: str, 
                 function_name: Optional[str] = None,
                 file_path: Optional[str] = None,
                 metadata: Optional[Dict[str, Any]] = None) -> CodeRecord:
        """
        Register code in both SimHash and AST databases.
        
        Args:
            code: Code to register
            function_name: Name of the function (optional)
            file_path: File path where code is located (optional)
            metadata: Additional metadata (optional)
            
        Returns:
            CodeRecord: The registered code record
        """
        # Register in SimHash database
        record = self.simhash_memory.register(code, function_name, file_path, metadata)
        
        # Register in AST database if available
        if self.enable_ast_analysis:
            try:
                self.ast_engine.add_function(code, function_name or "unknown")
            except Exception as e:
                self.logger.warning(f"Failed to register in AST database: {e}")
        
        return record
    
    def is_duplicate(self, code: str, use_ast_validation: bool = True) -> HybridResult:
        """
        Check if code is duplicate using hybrid detection.
        
        Args:
            code: Code to check for duplicates
            use_ast_validation: Whether to use AST for validation (default: True)
            
        Returns:
            HybridResult: Combined detection result
        """
        import time
        start_time = time.time()
        
        # Stage 1: Fast SimHash filtering
        simhash_start = time.time()
        simhash_result = self.simhash_memory.is_duplicate(code)
        simhash_time = time.time() - simhash_start
        
        performance_metrics = {
            "simhash_time": simhash_time,
            "ast_time": 0.0,
            "total_time": 0.0
        }
        
        # If no SimHash matches, return early
        if not simhash_result.is_duplicate:
            performance_metrics["total_time"] = time.time() - start_time
            return HybridResult(
                simhash_result=simhash_result,
                method_used="simhash_only",
                confidence=0.9,  # High confidence for no matches
                performance_metrics=performance_metrics
            )
        
        # Stage 2: AST validation (if enabled and available)
        ast_result = None
        if self.enable_ast_analysis and use_ast_validation:
            try:
                ast_start = time.time()
                ast_result = self.ast_engine.check_function_exists(code)
                performance_metrics["ast_time"] = time.time() - ast_start
                
                # Calculate confidence based on agreement between methods
                confidence = self._calculate_confidence(simhash_result, ast_result)
                method_used = "hybrid"
                
            except Exception as e:
                self.logger.warning(f"AST analysis failed: {e}")
                confidence = 0.7  # Lower confidence without AST validation
                method_used = "simhash_only"
        else:
            confidence = 0.8  # Medium confidence with SimHash only
            method_used = "simhash_only"
        
        performance_metrics["total_time"] = time.time() - start_time
        
        return HybridResult(
            simhash_result=simhash_result,
            ast_result=ast_result,
            method_used=method_used,
            confidence=confidence,
            performance_metrics=performance_metrics
        )
    
    def _calculate_confidence(self, simhash_result: SimilarityResult, ast_result: DuplicationResult) -> float:
        """Calculate confidence based on agreement between SimHash and AST analysis."""
        if simhash_result.is_duplicate and ast_result.is_duplicate:
            # Both agree on duplicate - high confidence
            return 0.95
        elif not simhash_result.is_duplicate and not ast_result.is_duplicate:
            # Both agree on no duplicate - high confidence
            return 0.95
        else:
            # Disagreement - medium confidence, prefer AST result
            return 0.6
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics for the hybrid system."""
        stats = {
            "simhash_stats": self.simhash_memory.similarity_detector.get_stats(),
            "ast_enabled": self.enable_ast_analysis,
            "has_ast_dedup": HAS_AST_DEDUP
        }
        
        if self.enable_ast_analysis and self.ast_engine:
            try:
                stats["ast_stats"] = {
                    "strategy": str(self.ast_engine.strategy),
                    "database_path": str(self.ast_engine.store.db_path)
                }
            except Exception as e:
                stats["ast_stats"] = {"error": str(e)}
        
        return stats
    
    def clear_memory(self):
        """Clear both SimHash and AST databases."""
        self.simhash_memory.clear_memory()
        
        if self.enable_ast_analysis and self.ast_engine:
            try:
                # Clear AST database
                self.ast_engine.cleanup_database()
            except Exception as e:
                self.logger.warning(f"Failed to clear AST database: {e}")
    
    def get_all_records(self) -> List[CodeRecord]:
        """Get all records from SimHash database."""
        return self.simhash_memory.get_all_records()


# Convenience function for easy usage
def create_hybrid_memory(db_path: str = "oopstracker.db", 
                        simhash_threshold: int = 12,
                        enable_ast: bool = True) -> HybridCodeMemory:
    """
    Create a hybrid code memory instance with sensible defaults.
    
    Args:
        db_path: Database path
        simhash_threshold: SimHash threshold (default: 12 for production)
        enable_ast: Whether to enable AST analysis
        
    Returns:
        HybridCodeMemory: Configured hybrid memory instance
    """
    return HybridCodeMemory(
        db_path=db_path,
        simhash_threshold=simhash_threshold,
        enable_ast_analysis=enable_ast
    )