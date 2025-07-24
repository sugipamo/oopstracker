"""Similarity-based clustering strategy using advanced similarity metrics."""

import re
import logging
from typing import List, Dict, Any, Tuple, Set
from collections import defaultdict
from difflib import SequenceMatcher
import hashlib

from .base import ClusterStrategy
from ...clustering_models import FunctionGroup


class SimilarityBasedClustering(ClusterStrategy):
    """Cluster functions based on advanced code similarity metrics."""
    
    def __init__(self, similarity_threshold: float = 0.7):
        """Initialize similarity-based clustering.
        
        Args:
            similarity_threshold: Minimum similarity score for clustering
        """
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.similarity_threshold = similarity_threshold
        self.min_cluster_size = 3
        
    async def cluster(self, functions: List[Dict[str, Any]]) -> List[FunctionGroup]:
        """Cluster functions based on multiple similarity metrics.
        
        Args:
            functions: List of function dictionaries
            
        Returns:
            List of function groups clustered by similarity
        """
        # First, group by structural patterns
        structural_groups = self._group_by_structural_patterns(functions)
        
        # Then, refine groups using advanced similarity metrics
        refined_clusters = []
        
        for group_name, group_functions in structural_groups.items():
            if len(group_functions) < self.min_cluster_size:
                continue
                
            # Further cluster using code similarity
            sub_clusters = self._cluster_by_code_similarity(group_functions)
            
            for i, sub_cluster in enumerate(sub_clusters):
                cluster_id = f"similarity_{group_name}_{i}" if len(sub_clusters) > 1 else f"similarity_{group_name}"
                cluster = FunctionGroup(
                    group_id=cluster_id,
                    functions=sub_cluster,
                    label=self._generate_cluster_label(sub_cluster, group_name),
                    confidence=self._calculate_cluster_confidence(sub_cluster),
                    metadata={
                        'clustering_strategy': 'similarity_based',
                        'base_pattern': group_name,
                        'function_count': len(sub_cluster),
                        'avg_similarity': self._calculate_average_similarity(sub_cluster)
                    }
                )
                refined_clusters.append(cluster)
        
        self.logger.info(f"Created {len(refined_clusters)} similarity-based clusters")
        return refined_clusters
    
    def _group_by_structural_patterns(self, functions: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group functions by structural patterns (name patterns, signatures, etc.)."""
        pattern_groups = defaultdict(list)
        
        # Enhanced patterns with more semantic meaning
        patterns = [
            # Data access patterns
            (r'^get_|^fetch_|^retrieve_|^load_|^read_', 'data_accessors'),
            (r'^set_|^update_|^modify_|^write_|^save_|^store_', 'data_mutators'),
            
            # Validation and checking
            (r'^is_|^has_|^can_|^should_|^must_', 'state_checkers'),
            (r'^validate_|^check_|^verify_|^ensure_|^assert_', 'validators'),
            
            # Processing and transformation
            (r'^handle_|^process_|^execute_|^run_|^perform_', 'processors'),
            (r'^convert_|^transform_|^parse_|^format_|^serialize_', 'transformers'),
            
            # Creation and initialization
            (r'^create_|^build_|^make_|^construct_|^initialize_|^setup_', 'factories'),
            
            # Utility and helpers
            (r'^calculate_|^compute_|^derive_|^analyze_', 'calculators'),
            (r'_helper$|_util$|_utility$', 'utilities'),
            
            # Event handling
            (r'^on_|^handle_.*_event|^.*_listener$|^.*_handler$', 'event_handlers'),
            
            # Testing
            (r'^test_|^assert_|^verify_.*_test', 'test_functions'),
            
            # Special methods
            (r'^__.*__$', 'special_methods'),
        ]
        
        # Also consider function signatures and complexity
        for func in functions:
            # Find matching pattern
            matched_pattern = None
            for pattern, group_name in patterns:
                if re.match(pattern, func['name'], re.IGNORECASE):
                    matched_pattern = group_name
                    break
            
            # If no pattern matched, analyze code structure
            if not matched_pattern:
                matched_pattern = self._analyze_code_structure(func)
            
            pattern_groups[matched_pattern].append(func)
        
        return pattern_groups
    
    def _analyze_code_structure(self, func: Dict[str, Any]) -> str:
        """Analyze code structure to determine function type."""
        code = func.get('code', '')
        
        # Simple heuristics based on code content
        if 'return' not in code and ('self.' in code or 'this.' in code):
            return 'state_modifiers'
        elif code.count('return') == 1 and len(code.split('\n')) < 5:
            return 'simple_accessors'
        elif 'for ' in code or 'while ' in code:
            return 'iterative_processors'
        elif 'if ' in code and code.count('if ') > 2:
            return 'conditional_logic'
        else:
            return 'general_functions'
    
    def _cluster_by_code_similarity(self, functions: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """Cluster functions by code similarity using multiple metrics."""
        if len(functions) <= self.min_cluster_size:
            return [functions]
        
        # Calculate similarity matrix
        n = len(functions)
        similarity_matrix = [[0.0] * n for _ in range(n)]
        
        for i in range(n):
            for j in range(i + 1, n):
                similarity = self._calculate_similarity(functions[i], functions[j])
                similarity_matrix[i][j] = similarity
                similarity_matrix[j][i] = similarity
        
        # Simple clustering based on similarity threshold
        clusters = []
        clustered = set()
        
        for i in range(n):
            if i in clustered:
                continue
            
            cluster = [functions[i]]
            clustered.add(i)
            
            for j in range(i + 1, n):
                if j not in clustered and similarity_matrix[i][j] >= self.similarity_threshold:
                    cluster.append(functions[j])
                    clustered.add(j)
            
            clusters.append(cluster)
        
        return [c for c in clusters if len(c) >= self.min_cluster_size]
    
    def _calculate_similarity(self, func1: Dict[str, Any], func2: Dict[str, Any]) -> float:
        """Calculate similarity between two functions using multiple metrics."""
        # Name similarity (Jaro-Winkler-like)
        name_sim = self._string_similarity(func1['name'], func2['name'])
        
        # Code structure similarity
        code_sim = self._code_similarity(func1.get('code', ''), func2.get('code', ''))
        
        # Length similarity
        len1 = len(func1.get('code', ''))
        len2 = len(func2.get('code', ''))
        length_sim = 1 - abs(len1 - len2) / max(len1, len2, 1)
        
        # Token similarity (simple tokenization)
        tokens1 = self._extract_tokens(func1.get('code', ''))
        tokens2 = self._extract_tokens(func2.get('code', ''))
        token_sim = self._jaccard_similarity(tokens1, tokens2)
        
        # Weighted average
        weights = [0.2, 0.4, 0.1, 0.3]  # name, code, length, tokens
        similarities = [name_sim, code_sim, length_sim, token_sim]
        
        return sum(w * s for w, s in zip(weights, similarities))
    
    def _string_similarity(self, s1: str, s2: str) -> float:
        """Calculate string similarity using SequenceMatcher."""
        return SequenceMatcher(None, s1, s2).ratio()
    
    def _code_similarity(self, code1: str, code2: str) -> float:
        """Calculate code similarity considering structure."""
        # Normalize code (remove comments, extra whitespace)
        norm1 = self._normalize_code(code1)
        norm2 = self._normalize_code(code2)
        
        # Use SequenceMatcher for structural similarity
        return SequenceMatcher(None, norm1, norm2).ratio()
    
    def _normalize_code(self, code: str) -> str:
        """Normalize code for comparison."""
        # Remove comments (simple approach)
        lines = []
        for line in code.split('\n'):
            # Remove inline comments
            if '#' in line:
                line = line[:line.index('#')]
            line = line.strip()
            if line:
                lines.append(line)
        
        return '\n'.join(lines)
    
    def _extract_tokens(self, code: str) -> Set[str]:
        """Extract meaningful tokens from code."""
        # Simple tokenization - can be enhanced with proper lexing
        tokens = set()
        
        # Extract identifiers (variable/function names)
        identifier_pattern = r'\b[a-zA-Z_][a-zA-Z0-9_]*\b'
        tokens.update(re.findall(identifier_pattern, code))
        
        # Extract string literals
        string_pattern = r'["\']([^"\']*)["\']'
        tokens.update(re.findall(string_pattern, code))
        
        return tokens
    
    def _jaccard_similarity(self, set1: Set[str], set2: Set[str]) -> float:
        """Calculate Jaccard similarity between two sets."""
        if not set1 and not set2:
            return 1.0
        
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        return intersection / union if union > 0 else 0.0
    
    def _generate_cluster_label(self, functions: List[Dict[str, Any]], base_pattern: str) -> str:
        """Generate a descriptive label for the cluster."""
        # Extract common prefix/suffix from function names
        names = [f['name'] for f in functions]
        common_prefix = self._find_common_prefix(names)
        common_suffix = self._find_common_suffix(names)
        
        if common_prefix and len(common_prefix) > 3:
            label = f"{common_prefix}* functions"
        elif common_suffix and len(common_suffix) > 3:
            label = f"*{common_suffix} functions"
        else:
            label = base_pattern.replace('_', ' ').title()
        
        return label
    
    def _find_common_prefix(self, strings: List[str]) -> str:
        """Find common prefix among strings."""
        if not strings:
            return ""
        
        prefix = strings[0]
        for s in strings[1:]:
            while not s.startswith(prefix):
                prefix = prefix[:-1]
                if not prefix:
                    return ""
        return prefix
    
    def _find_common_suffix(self, strings: List[str]) -> str:
        """Find common suffix among strings."""
        if not strings:
            return ""
        
        suffix = strings[0]
        for s in strings[1:]:
            while not s.endswith(suffix):
                suffix = suffix[1:]
                if not suffix:
                    return ""
        return suffix
    
    def _calculate_cluster_confidence(self, functions: List[Dict[str, Any]]) -> float:
        """Calculate confidence score for the cluster."""
        if len(functions) < 2:
            return 0.5
        
        # Calculate average pairwise similarity
        total_similarity = 0
        count = 0
        
        for i in range(len(functions)):
            for j in range(i + 1, len(functions)):
                total_similarity += self._calculate_similarity(functions[i], functions[j])
                count += 1
        
        avg_similarity = total_similarity / count if count > 0 else 0
        
        # Confidence is higher when similarities are high and cluster size is reasonable
        size_factor = min(1.0, len(functions) / 10)  # Peaks at 10 functions
        
        return avg_similarity * 0.7 + size_factor * 0.3
    
    def _calculate_average_similarity(self, functions: List[Dict[str, Any]]) -> float:
        """Calculate average similarity within the cluster."""
        if len(functions) < 2:
            return 1.0
        
        total = 0
        count = 0
        
        for i in range(len(functions)):
            for j in range(i + 1, len(functions)):
                total += self._calculate_similarity(functions[i], functions[j])
                count += 1
        
        return total / count if count > 0 else 0
    
    def get_strategy_name(self) -> str:
        """Get the name of the clustering strategy."""
        return "similarity_based"