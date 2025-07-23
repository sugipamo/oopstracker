"""
AST-based SimHash duplicate detection with layered architecture.
This is the refactored version using separated layers for different responsibilities.
"""

import logging
from typing import List, Dict, Optional, Tuple, Any

from .models import CodeRecord, SimilarityResult
from .layers import (
    DataManagementLayer,
    SimilarityDetectionLayer,
    GraphConstructionLayer,
    StatisticsAnalysisLayer
)
from .detectors import DetectorCacheManager

logger = logging.getLogger(__name__)


class ASTSimHashDetectorLayered:
    """
    AST-based SimHash detector with layered architecture.
    
    This refactored version separates concerns into specialized layers:
    - DataManagementLayer: Handles data persistence and memory management
    - SimilarityDetectionLayer: Handles similarity detection and duplicate finding
    - GraphConstructionLayer: Handles similarity graph construction
    - StatisticsAnalysisLayer: Handles statistics collection and analysis
    """
    
    def __init__(self, hamming_threshold: int = 10, 
                 db_path: str = "oopstracker_ast.db", 
                 include_tests: bool = False):
        """
        Initialize layered AST SimHash detector.
        
        Args:
            hamming_threshold: Maximum Hamming distance for similarity
            db_path: Path to SQLite database for persistence
            include_tests: Whether to include test functions in analysis
        """
        self.hamming_threshold = hamming_threshold
        self.include_tests = include_tests
        
        # Initialize layers
        self.data_layer = DataManagementLayer(db_path)
        self.similarity_layer = SimilarityDetectionLayer(
            hamming_threshold, include_tests
        )
        self.graph_layer = GraphConstructionLayer()
        self.statistics_layer = StatisticsAnalysisLayer()
        
        # Cache manager (cross-layer concern)
        self.cache_manager = DetectorCacheManager()
        
        # Load existing data
        loaded, skipped = self.data_layer.load_existing_data()
        logger.info(
            f"Initialized layered detector with threshold {hamming_threshold}, "
            f"loaded {loaded} records, skipped {skipped}"
        )
    
    # Data Management Methods (delegated to data layer)
    
    def register_file(self, file_path: str, force: bool = False) -> List[CodeRecord]:
        """Register all functions and classes from a Python file."""
        return self.data_layer.register_file(file_path, force)
    
    def register_code(self, source_code: str, 
                      function_name: Optional[str] = None,
                      file_path: Optional[str] = None) -> Optional[CodeRecord]:
        """Register a single piece of code."""
        return self.data_layer.register_code(source_code, function_name, file_path)
    
    def get_all_records(self) -> List[CodeRecord]:
        """Get all registered records."""
        return self.data_layer.get_all_records()
    
    def clear_memory(self):
        """Clear all stored data."""
        self.data_layer.clear_all()
        self.cache_manager.clear_cache()
        logger.info("Cleared layered detector memory and cache")
    
    # Similarity Detection Methods (delegated to similarity layer)
    
    def find_similar(self, source_code: str, 
                     function_name: Optional[str] = None,
                     threshold: float = 0.7) -> SimilarityResult:
        """Find similar code to the given source."""
        return self.similarity_layer.find_similar(
            source_code, self.data_layer, function_name, threshold
        )
    
    def find_potential_duplicates(self, threshold: float = 0.8, 
                                  use_fast_mode: bool = True,
                                  use_cache: bool = True, 
                                  include_trivial: bool = False,
                                  silent: bool = False, 
                                  top_percent: Optional[float] = None) -> List[Tuple[CodeRecord, CodeRecord, float]]:
        """Find potential duplicate pairs across all registered code."""
        # Check cache
        if use_cache and top_percent is None:
            cache_key = self.cache_manager.get_cache_key(
                threshold, use_fast_mode, include_trivial, 
                len(self.data_layer.records)
            )
            records = self.data_layer.get_all_records()
            current_timestamp = max(
                (r.timestamp for r in records), 
                default=0
            )
            
            cached_result = self.cache_manager.get_cached_result(
                cache_key, current_timestamp
            )
            if cached_result is not None:
                return cached_result
        
        # Find duplicates
        duplicates = self.similarity_layer.find_potential_duplicates(
            self.data_layer, threshold, use_fast_mode, 
            include_trivial, silent, top_percent
        )
        
        # Update cache
        if use_cache and top_percent is None:
            self.cache_manager.cache_result(cache_key, duplicates, current_timestamp)
        
        return duplicates
    
    def get_related_units(self, code_hash: str, 
                          threshold: float = 0.3,
                          max_results: int = 10) -> List[Tuple[CodeRecord, float]]:
        """Get units related to a specific code unit."""
        return self.similarity_layer.get_related_units(
            code_hash, self.data_layer, threshold, max_results
        )
    
    # Graph Construction Methods (delegated to graph layer)
    
    def build_similarity_graph(self, threshold: float = 0.3, 
                               use_fast_mode: bool = True) -> Dict[str, List[Tuple[str, float]]]:
        """Build a similarity graph."""
        return self.graph_layer.build_similarity_graph(
            self.data_layer, threshold, use_fast_mode
        )
    
    def find_relations_adaptive(self, target_connections: int = 200, 
                                max_connections: int = 1000,
                                min_threshold: float = 0.1, 
                                max_threshold: float = 0.9,
                                use_fast_mode: bool = True) -> Tuple[Dict[str, List[Tuple[str, float]]], float]:
        """Build similarity graph with adaptive threshold."""
        return self.graph_layer.find_relations_adaptive(
            self.data_layer, target_connections, max_connections,
            min_threshold, max_threshold, use_fast_mode
        )
    
    # Statistics Methods (delegated to statistics layer)
    
    def get_statistics(self) -> Dict:
        """Get statistics about registered code."""
        return self.statistics_layer.get_statistics(
            self.data_layer, self.hamming_threshold
        )
    
    def analyze_code_structure(self, source_code: str, 
                               file_path: Optional[str] = None) -> Dict:
        """Analyze the structure of given source code."""
        return self.statistics_layer.analyze_code_structure(
            source_code, file_path
        )
    
    def generate_quality_report(self) -> Dict:
        """Generate a comprehensive code quality report."""
        return self.statistics_layer.generate_quality_report(self.data_layer)
    
    # Additional convenience methods
    
    def analyze_graph_structure(self, threshold: float = 0.3) -> Dict:
        """Build graph and analyze its structure."""
        graph = self.build_similarity_graph(threshold)
        return self.graph_layer.analyze_graph_components(graph)
    
    def find_code_clusters(self, threshold: float = 0.5, 
                           min_cluster_size: int = 3) -> List[List[CodeRecord]]:
        """Find clusters of similar code."""
        graph = self.build_similarity_graph(threshold)
        clusters = self.graph_layer.find_clusters(graph, min_cluster_size)
        
        # Convert from hashes to records
        record_clusters = []
        for cluster in clusters:
            records = []
            for hash in cluster:
                record = self.data_layer.get_record(hash)
                if record:
                    records.append(record)
            if records:
                record_clusters.append(records)
        
        return record_clusters