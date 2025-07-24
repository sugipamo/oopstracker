"""
Efficient LLM-based duplicate detector using the original SmartGroupSplitter design.
Uses 10 samples → regex generation → binary split approach.
"""

import asyncio
import logging
import random
from typing import List, Dict, Any

from .code_record import CodeRecord
from .similarity_result import SimilarityResult
from .unified_detector import DuplicateDetector, DetectionConfiguration
from .smart_group_splitter import SmartGroupSplitter
from .function_group_clustering import FunctionGroup, FunctionGroupClusteringSystem


class EfficientLLMDetector(DuplicateDetector):
    """Efficient LLM-based detector using group splitting approach."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.clustering_system = FunctionGroupClusteringSystem()
        self.group_splitter = SmartGroupSplitter()
        self.min_group_size_for_splitting = 10
    
    def detect_duplicates(self, records: List[CodeRecord], config: DetectionConfiguration) -> List[SimilarityResult]:
        """Detect duplicates using efficient group-based LLM analysis."""
        if len(records) < 2:
            return []
        
        self.logger.info(f"Starting efficient LLM-based duplicate detection for {len(records)} records")
        
        try:
            # Step 1: Convert records to function format
            functions = self._convert_records_to_functions(records)
            if len(functions) < 2:
                return []
            
            # Step 2: Simple initial clustering (synchronous for now)
            clusters = self._create_simple_clusters(functions)
            
            # Step 3: Use SmartGroupSplitter for large groups (if needed)
            refined_clusters = self._refine_clusters_sync(clusters)
            
            # Step 4: Find duplicates within refined clusters
            duplicates = self._find_duplicates_in_clusters(refined_clusters, config)
            
            self.logger.info(f"Efficient LLM analysis completed, found {len(duplicates)} duplicate pairs")
            return duplicates
            
        except Exception as e:
            self.logger.error(f"Efficient LLM duplicate detection failed: {e}")
            raise RuntimeError(f"LLM is required but failed: {e}")
    
    def _convert_records_to_functions(self, records: List[CodeRecord]) -> List[Dict]:
        """Convert CodeRecord objects to function dictionaries."""
        functions = []
        for record in records:
            if record.code_content and record.function_name:
                functions.append({
                    'name': record.function_name,
                    'code': record.code_content,
                    'file': record.file_path or 'unknown',
                    'signature': '',
                    'category': 'function',
                    'line_number': record.metadata.get('line_number', 0) if record.metadata else 0,
                    'metadata': {
                        'hash': record.code_hash,
                        'complexity': 1,
                        'dependencies': []
                    },
                    '_record': record  # Keep reference to original record
                })
        return functions
    
    async def _create_initial_clusters(self, functions: List[Dict]) -> List[FunctionGroup]:
        """Create initial clusters using the clustering system."""
        try:
            clusters = await self.clustering_system.get_current_function_clusters(functions)
            self.logger.info(f"Created {len(clusters)} initial clusters")
            return clusters
        except Exception as e:
            self.logger.warning(f"Initial clustering failed: {e}, creating single cluster")
            # Fallback: create one large cluster
            return [FunctionGroup(
                group_id="all_functions",
                functions=functions,
                label="All Functions",
                confidence=0.5,
                metadata={}
            )]
    
    async def _refine_large_clusters(self, clusters: List[FunctionGroup]) -> List[FunctionGroup]:
        """Refine large clusters using SmartGroupSplitter."""
        refined_clusters = []
        
        for cluster in clusters:
            if len(cluster.functions) >= self.min_group_size_for_splitting:
                self.logger.info(f"Splitting large cluster '{cluster.label}' with {len(cluster.functions)} functions")
                try:
                    # Use SmartGroupSplitter's LLM-based splitting
                    split_results = await self.group_splitter.split_large_groups_with_llm([cluster])
                    refined_clusters.extend(split_results)
                    self.logger.info(f"Split into {len(split_results)} sub-clusters")
                except Exception as e:
                    self.logger.warning(f"Failed to split cluster '{cluster.label}': {e}")
                    refined_clusters.append(cluster)  # Keep original if splitting fails
            else:
                refined_clusters.append(cluster)
        
        return refined_clusters
    
    def _find_duplicates_in_clusters(self, clusters: List[FunctionGroup], config: DetectionConfiguration) -> List[SimilarityResult]:
        """Find duplicates within each cluster using exact matching."""
        duplicates = []
        
        for cluster in clusters:
            cluster_duplicates = self._find_exact_duplicates_in_cluster(cluster, config)
            duplicates.extend(cluster_duplicates)
        
        return duplicates
    
    def _find_exact_duplicates_in_cluster(self, cluster: FunctionGroup, config: DetectionConfiguration) -> List[SimilarityResult]:
        """Find exact duplicates within a single cluster."""
        duplicates = []
        functions = cluster.functions
        
        # Group by normalized code content
        code_groups = {}
        for func in functions:
            normalized_code = self._normalize_code(func['code'])
            if normalized_code not in code_groups:
                code_groups[normalized_code] = []
            code_groups[normalized_code].append(func)
        
        # Find groups with multiple functions (duplicates)
        for normalized_code, func_group in code_groups.items():
            if len(func_group) >= 2:
                # Create similarity results for all pairs in the group
                for i in range(len(func_group)):
                    for j in range(i + 1, len(func_group)):
                        func1, func2 = func_group[i], func_group[j]
                        
                        # Calculate similarity (should be high for functions in same split group)
                        similarity = self._calculate_semantic_similarity(func1, func2)
                        
                        if similarity >= config.threshold:
                            result = SimilarityResult(
                                is_duplicate=True,
                                similarity_score=similarity,
                                matched_records=[func1['_record'], func2['_record']],
                                analysis_method="llm_group_based",
                                threshold=config.threshold
                            )
                            result.add_metadata('cluster_id', cluster.group_id)
                            result.add_metadata('cluster_label', cluster.label)
                            duplicates.append(result)
        
        return duplicates
    
    def _normalize_code(self, code: str) -> str:
        """Normalize code for comparison."""
        # Remove comments, whitespace, and variable names for structural comparison
        import re
        
        # Remove comments
        code = re.sub(r'#.*$', '', code, flags=re.MULTILINE)
        
        # Remove docstrings
        code = re.sub(r'""".*?"""', '', code, flags=re.DOTALL)
        code = re.sub(r"'''.*?'''", '', code, flags=re.DOTALL)
        
        # Normalize whitespace
        code = re.sub(r'\s+', ' ', code)
        
        # Remove variable names (simple approach)
        code = re.sub(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', 'VAR', code)
        
        return code.strip().lower()
    
    def _calculate_semantic_similarity(self, func1: Dict, func2: Dict) -> float:
        """Calculate semantic similarity between two functions."""
        # Since functions are in the same LLM-generated group, they should be similar
        # Use a combination of factors:
        
        # 1. Normalized code similarity
        norm1 = self._normalize_code(func1['code'])
        norm2 = self._normalize_code(func2['code'])
        
        if norm1 == norm2:
            return 1.0  # Exact structural match
        
        # 2. Function name similarity
        name1 = func1['name'].lower()
        name2 = func2['name'].lower()
        
        # Check for common patterns
        common_prefixes = ['get_', 'set_', 'is_', 'has_', 'can_', 'should_', 'validate_', 'check_']
        same_prefix = any(name1.startswith(prefix) and name2.startswith(prefix) for prefix in common_prefixes)
        
        if same_prefix:
            return 0.85  # High similarity for same operation type
        
        # 3. Code length similarity
        len1, len2 = len(func1['code']), len(func2['code'])
        length_ratio = min(len1, len2) / max(len1, len2) if max(len1, len2) > 0 else 1.0
        
        # 4. Basic similarity score
        base_similarity = 0.7 * length_ratio
        
        return min(base_similarity, 0.95)  # Cap at 0.95 to indicate non-exact match
    
    def find_similar(self, source_code: str, records: List[CodeRecord], config: DetectionConfiguration) -> SimilarityResult:
        """Find similar code using efficient group-based analysis."""
        if not source_code.strip():
            return SimilarityResult(False, 0.0, [], "llm_group_based", config.threshold)
        
        # Create a temporary record for the source code
        source_record = CodeRecord(
            code_content=source_code,
            function_name="query_function",
            file_path="<query>"
        )
        
        # Add source to records and detect duplicates
        all_records = [source_record] + records
        duplicates = self.detect_duplicates(all_records, config)
        
        # Filter results that involve the source record
        matched_records = []
        max_similarity = 0.0
        
        for dup in duplicates:
            if source_record in dup.matched_records:
                other_records = [r for r in dup.matched_records if r != source_record]
                matched_records.extend(other_records)
                max_similarity = max(max_similarity, dup.similarity_score)
        
        return SimilarityResult(
            is_duplicate=len(matched_records) > 0,
            similarity_score=max_similarity,
            matched_records=matched_records,
            analysis_method="llm_group_based",
            threshold=config.threshold
        )
    
    def get_algorithm_name(self) -> str:
        return "llm_group_based"