"""
Specialized detector components for AST SimHash detection.

This module contains extracted components that handle specific responsibilities
in the duplicate detection process.
"""

import logging
from typing import List, Dict, Optional, Tuple, Set
from collections import defaultdict

from .ast_analyzer import ASTAnalyzer, CodeUnit
from .models import CodeRecord, SimilarityResult
from .simhash_detector import BKTree
from .code_filter_utility import CodeFilterUtility
from .progress_reporter import ProgressReporter

logger = logging.getLogger(__name__)


class SimilarityDetector:
    """
    Core duplicate detection logic.
    
    Handles the actual similarity calculation and duplicate finding operations.
    """
    
    def __init__(self, analyzer: ASTAnalyzer, code_filter: CodeFilterUtility):
        self.analyzer = analyzer
        self.code_filter = code_filter
    
    def calculate_similarity(self, unit1: CodeUnit, unit2: CodeUnit) -> float:
        """Calculate structural similarity between two code units."""
        return self.analyzer.calculate_structural_similarity(unit1, unit2)
    
    def find_duplicates(self, code_units: Dict[str, CodeUnit], 
                       threshold: float = 0.8) -> List[Tuple[str, str, float]]:
        """Find duplicate code units based on similarity threshold."""
        duplicates = []
        processed = set()
        
        for hash1, unit1 in code_units.items():
            if not self.code_filter.should_include_unit(unit1):
                continue
                
            for hash2, unit2 in code_units.items():
                if hash1 >= hash2 or hash2 in processed:
                    continue
                    
                if not self.code_filter.should_include_unit(unit2):
                    continue
                
                similarity = self.calculate_similarity(unit1, unit2)
                if similarity >= threshold:
                    duplicates.append((hash1, hash2, similarity))
            
            processed.add(hash1)
        
        return duplicates
    
    def find_duplicates_fast(self, records: List[CodeRecord], code_units: Dict[str, CodeUnit],
                            bk_tree: BKTree, threshold: float, hamming_threshold: int,
                            include_trivial: bool = False, silent: bool = False) -> List[Tuple[CodeRecord, CodeRecord, float]]:
        """Find duplicates using fast SimHash pre-filtering."""
        duplicates = []
        processed_pairs = set()
        
        # Setup progress reporting
        total_records = len(records)
        progress_reporter = None if silent else ProgressReporter(total_records, "Finding duplicates (fast mode)")
        
        for i, record1 in enumerate(records):
            if progress_reporter:
                progress_reporter.update(i)
            
            unit1 = code_units.get(record1.code_hash)
            if not unit1:
                continue
            
            # Skip if trivial and not including trivial
            if not include_trivial and not self.code_filter.should_include_unit(unit1):
                continue
            
            # Find candidates using BK-tree
            hamming_dist = max(3, int(64 * (1.0 - threshold)))
            candidates = bk_tree.search(record1.simhash, hamming_dist)
            
            for candidate_record, _ in candidates:
                if record1.code_hash >= candidate_record.code_hash:
                    continue
                
                pair_key = (min(record1.code_hash, candidate_record.code_hash),
                           max(record1.code_hash, candidate_record.code_hash))
                if pair_key in processed_pairs:
                    continue
                
                processed_pairs.add(pair_key)
                
                unit2 = code_units.get(candidate_record.code_hash)
                if not unit2:
                    continue
                
                # Skip if trivial and not including trivial
                if not include_trivial and not self.code_filter.should_include_unit(unit2):
                    continue
                
                # Calculate actual similarity
                similarity = self.calculate_similarity(unit1, unit2)
                if similarity >= threshold:
                    duplicates.append((record1, candidate_record, similarity))
        
        if progress_reporter:
            progress_reporter.finish()
        
        # Sort by similarity
        duplicates.sort(key=lambda x: x[2], reverse=True)
        logger.info(f"Found {len(duplicates)} duplicate pairs using fast mode")
        
        return duplicates
    
    def find_duplicates_exhaustive(self, records: List[CodeRecord], code_units: Dict[str, CodeUnit],
                                  threshold: float, include_trivial: bool = False,
                                  silent: bool = False) -> List[Tuple[CodeRecord, CodeRecord, float]]:
        """Find duplicates using exhaustive comparison."""
        duplicates = []
        
        # Setup progress reporting
        total_comparisons = len(records) * (len(records) - 1) // 2
        progress_reporter = None if silent else ProgressReporter(total_comparisons, "Finding duplicates (exhaustive)")
        comparison_count = 0
        
        for i, record1 in enumerate(records):
            unit1 = code_units.get(record1.code_hash)
            if not unit1:
                continue
            
            # Skip if trivial and not including trivial
            if not include_trivial and not self.code_filter.should_include_unit(unit1):
                continue
            
            for j in range(i + 1, len(records)):
                if progress_reporter:
                    progress_reporter.update(comparison_count)
                    comparison_count += 1
                
                record2 = records[j]
                unit2 = code_units.get(record2.code_hash)
                if not unit2:
                    continue
                
                # Skip if trivial and not including trivial
                if not include_trivial and not self.code_filter.should_include_unit(unit2):
                    continue
                
                # Calculate similarity
                similarity = self.calculate_similarity(unit1, unit2)
                if similarity >= threshold:
                    duplicates.append((record1, record2, similarity))
        
        if progress_reporter:
            progress_reporter.finish()
        
        # Sort by similarity
        duplicates.sort(key=lambda x: x[2], reverse=True)
        logger.info(f"Found {len(duplicates)} duplicate pairs using exhaustive mode")
        
        return duplicates


class SimilarityGraphBuilder:
    """
    Builds and manages similarity graphs between code units.
    """
    
    def __init__(self, analyzer: ASTAnalyzer):
        self.analyzer = analyzer
    
    def build_graph(self, code_units: Dict[str, CodeUnit], 
                   threshold: float = 0.3) -> Dict[str, List[Tuple[str, float]]]:
        """Build a similarity graph with edges above the threshold."""
        graph = defaultdict(list)
        
        unit_list = list(code_units.items())
        for i, (hash1, unit1) in enumerate(unit_list):
            for j in range(i + 1, len(unit_list)):
                hash2, unit2 = unit_list[j]
                
                similarity = self.analyzer.calculate_structural_similarity(unit1, unit2)
                if similarity >= threshold:
                    graph[hash1].append((hash2, similarity))
                    graph[hash2].append((hash1, similarity))
        
        # Sort connections by similarity
        for node in graph:
            graph[node].sort(key=lambda x: x[1], reverse=True)
        
        return dict(graph)
    
    def get_strongly_connected_components(self, graph: Dict[str, List[Tuple[str, float]]], 
                                        min_connections: int = 2) -> List[Set[str]]:
        """Find strongly connected components in the similarity graph."""
        components = []
        visited = set()
        
        for node in graph:
            if node in visited:
                continue
            
            component = set()
            stack = [node]
            
            while stack:
                current = stack.pop()
                if current in visited:
                    continue
                
                visited.add(current)
                component.add(current)
                
                # Add neighbors with sufficient connections
                neighbors = [n for n, _ in graph.get(current, [])]
                for neighbor in neighbors:
                    if neighbor not in visited and len(graph.get(neighbor, [])) >= min_connections:
                        stack.append(neighbor)
            
            if len(component) >= min_connections:
                components.append(component)
        
        return components
    
    def build_similarity_graph_fast(self, records: List[CodeRecord], code_units: Dict[str, CodeUnit],
                                   bk_tree: BKTree, threshold: float) -> Dict[str, List[Tuple[str, float]]]:
        """Build similarity graph using fast SimHash pre-filtering."""
        graph = defaultdict(list)
        
        for record in records:
            unit = code_units.get(record.code_hash)
            if not unit:
                continue
            
            # Find candidates using BK-tree
            hamming_dist = max(3, int(64 * (1.0 - threshold)))
            candidates = bk_tree.search(record.simhash, hamming_dist)
            
            for candidate_record, _ in candidates:
                if record.code_hash == candidate_record.code_hash:
                    continue
                
                candidate_unit = code_units.get(candidate_record.code_hash)
                if not candidate_unit:
                    continue
                
                # Calculate actual similarity
                similarity = self.analyzer.calculate_structural_similarity(unit, candidate_unit)
                if similarity >= threshold:
                    graph[record.code_hash].append((candidate_record.code_hash, similarity))
        
        # Sort connections by similarity
        for node in graph:
            graph[node].sort(key=lambda x: x[1], reverse=True)
        
        return dict(graph)
    
    def build_similarity_graph_full(self, records: List[CodeRecord], code_units: Dict[str, CodeUnit],
                                   threshold: float) -> Dict[str, List[Tuple[str, float]]]:
        """Build similarity graph using exhaustive comparison."""
        return self.build_graph(code_units, threshold)


class DetectorCacheManager:
    """
    Manages caching for detector operations.
    """
    
    def __init__(self):
        self.similarity_cache: Dict[Tuple[str, str], float] = {}
        self.unit_cache: Dict[str, CodeUnit] = {}
        self.result_cache: Dict[str, Tuple[List, float]] = {}  # cache_key -> (result, timestamp)
    
    def get_cached_similarity(self, hash1: str, hash2: str) -> Optional[float]:
        """Get cached similarity score between two code units."""
        key = (min(hash1, hash2), max(hash1, hash2))
        return self.similarity_cache.get(key)
    
    def cache_similarity(self, hash1: str, hash2: str, similarity: float):
        """Cache similarity score between two code units."""
        key = (min(hash1, hash2), max(hash1, hash2))
        self.similarity_cache[key] = similarity
    
    def cache_unit(self, code_hash: str, unit: CodeUnit):
        """Cache a code unit."""
        self.unit_cache[code_hash] = unit
    
    def get_cached_unit(self, code_hash: str) -> Optional[CodeUnit]:
        """Get cached code unit."""
        return self.unit_cache.get(code_hash)
    
    def get_cache_key(self, threshold: float, use_fast_mode: bool, 
                     include_trivial: bool, record_count: int) -> str:
        """Generate cache key for duplicate detection results."""
        return f"{threshold}_{use_fast_mode}_{include_trivial}_{record_count}"
    
    def get_cached_result(self, cache_key: str, current_timestamp: float) -> Optional[List]:
        """Get cached result if it's still valid."""
        if cache_key in self.result_cache:
            result, timestamp = self.result_cache[cache_key]
            if timestamp >= current_timestamp:
                logger.info(f"Using cached result for key {cache_key}")
                return result
        return None
    
    def cache_result(self, cache_key: str, result: List, timestamp: float):
        """Cache detection result."""
        self.result_cache[cache_key] = (result, timestamp)
    
    def clear_cache(self):
        """Clear all caches."""
        self.similarity_cache.clear()
        self.unit_cache.clear()
        self.result_cache.clear()


class AdaptiveThresholdFinder:
    """
    Finds optimal similarity thresholds based on graph structure.
    """
    
    def __init__(self, graph_builder: SimilarityGraphBuilder):
        self.graph_builder = graph_builder
    
    def find_threshold(self, code_units: Dict[str, CodeUnit], 
                      target_connections: int = 200,
                      min_threshold: float = 0.1,
                      max_threshold: float = 0.9) -> float:
        """Find threshold that produces target number of connections."""
        low, high = min_threshold, max_threshold
        best_threshold = high
        
        while high - low > 0.01:
            mid = (low + high) / 2
            graph = self.graph_builder.build_graph(code_units, threshold=mid)
            
            total_connections = sum(len(edges) for edges in graph.values()) // 2
            
            if total_connections > target_connections:
                low = mid
            else:
                high = mid
                best_threshold = mid
        
        return best_threshold
    
    def find_adaptive_threshold(self, records: List[CodeRecord], code_units: Dict[str, CodeUnit],
                               bk_tree: BKTree, target_connections: int, max_connections: int,
                               min_threshold: float, max_threshold: float, 
                               use_fast_mode: bool) -> Tuple[Dict[str, List[Tuple[str, float]]], float]:
        """Find adaptive threshold and build graph."""
        low, high = min_threshold, max_threshold
        best_threshold = high
        best_graph = {}
        
        while high - low > 0.01:
            mid = (low + high) / 2
            
            if use_fast_mode:
                graph = self.graph_builder.build_similarity_graph_fast(
                    records, code_units, bk_tree, mid
                )
            else:
                graph = self.graph_builder.build_similarity_graph_full(
                    records, code_units, mid
                )
            
            total_connections = sum(len(edges) for edges in graph.values()) // 2
            
            if total_connections > max_connections:
                low = mid
            elif total_connections < target_connections:
                high = mid
                best_threshold = mid
                best_graph = graph
            else:
                best_threshold = mid
                best_graph = graph
                break
        
        logger.info(f"Adaptive threshold: {best_threshold:.3f} with {sum(len(edges) for edges in best_graph.values()) // 2} connections")
        return best_graph, best_threshold


class StatisticsCollector:
    """
    Collects and calculates statistics about code units.
    """
    
    def __init__(self):
        self.stats = {}
    
    def collect_statistics(self, code_units: Dict[str, CodeUnit], 
                         records: Dict[str, CodeRecord]) -> Dict:
        """Collect comprehensive statistics about the code base."""
        stats = {
            'total_units': len(code_units),
            'total_files': len(set(r.file_path for r in records.values())),
            'complexity_distribution': self._calculate_complexity_distribution(code_units),
            'size_distribution': self._calculate_size_distribution(code_units),
            'type_distribution': self._calculate_type_distribution(code_units)
        }
        
        self.stats = stats
        return stats
    
    def _calculate_complexity_distribution(self, code_units: Dict[str, CodeUnit]) -> Dict:
        """Calculate distribution of code complexity."""
        complexities = [unit.metrics.get('complexity', 0) for unit in code_units.values()]
        if not complexities:
            return {}
        
        return {
            'min': min(complexities),
            'max': max(complexities),
            'mean': sum(complexities) / len(complexities),
            'quartiles': self._calculate_quartiles(complexities)
        }
    
    def _calculate_size_distribution(self, code_units: Dict[str, CodeUnit]) -> Dict:
        """Calculate distribution of code sizes."""
        sizes = [unit.metrics.get('size', 0) for unit in code_units.values()]
        if not sizes:
            return {}
        
        return {
            'min': min(sizes),
            'max': max(sizes),
            'mean': sum(sizes) / len(sizes),
            'quartiles': self._calculate_quartiles(sizes)
        }
    
    def _calculate_type_distribution(self, code_units: Dict[str, CodeUnit]) -> Dict:
        """Calculate distribution of code unit types."""
        type_counts = defaultdict(int)
        for unit in code_units.values():
            type_counts[unit.node_type] += 1
        return dict(type_counts)
    
    def _calculate_quartiles(self, values: List[float]) -> List[float]:
        """Calculate quartiles for a list of values."""
        if not values:
            return []
        
        sorted_values = sorted(values)
        n = len(sorted_values)
        
        return [
            sorted_values[n // 4],
            sorted_values[n // 2],
            sorted_values[3 * n // 4]
        ]


class TopPercentDuplicateFinder:
    """
    Finds top percentage of duplicate code.
    """
    
    def __init__(self, similarity_detector: SimilarityDetector, 
                 hamming_threshold: int = 10):
        self.similarity_detector = similarity_detector
        self.hamming_threshold = hamming_threshold
    
    def find_top_percent(self, code_units: Dict[str, CodeUnit], 
                        top_percent: float = 10.0) -> List[Tuple[str, str, float]]:
        """Find top N% of most similar code pairs."""
        all_similarities = []
        
        unit_list = list(code_units.items())
        for i, (hash1, unit1) in enumerate(unit_list):
            for j in range(i + 1, len(unit_list)):
                hash2, unit2 = unit_list[j]
                
                similarity = self.similarity_detector.calculate_similarity(unit1, unit2)
                if similarity > 0:  # Only include non-zero similarities
                    all_similarities.append((hash1, hash2, similarity))
        
        # Sort by similarity
        all_similarities.sort(key=lambda x: x[2], reverse=True)
        
        # Calculate how many pairs to return
        target_count = max(1, int(len(all_similarities) * (top_percent / 100.0)))
        
        return all_similarities[:target_count]