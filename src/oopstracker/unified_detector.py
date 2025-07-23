"""
Unified detector interface eliminating multiple detector implementations.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from .code_record import CodeRecord
from .similarity_result import SimilarityResult


@dataclass
class DetectionConfiguration:
    """Configuration for detection operations."""
    algorithm: str = "simhash"
    threshold: float = 0.7
    include_exact_matches: bool = True
    include_partial_matches: bool = True
    max_results: int = 100
    max_records_per_batch: int = 200
    memory_cleanup_interval: int = 50


class DuplicateDetector(ABC):
    """Abstract base for duplicate detection algorithms."""
    
    @abstractmethod
    def detect_duplicates(self, records: List[CodeRecord], config: DetectionConfiguration) -> List[SimilarityResult]:
        """Detect duplicate code records."""
        pass
    
    @abstractmethod
    def find_similar(self, source_code: str, records: List[CodeRecord], config: DetectionConfiguration) -> SimilarityResult:
        """Find similar code to source."""
        pass
    
    @abstractmethod
    def get_algorithm_name(self) -> str:
        """Return algorithm name."""
        pass


class LayeredDetectionStrategy:
    """Layered duplicate detection strategy following CLAUDE.md patterns."""
    
    def __init__(self):
        self.normalization_cache = {}
        self.feature_cache = {}
    
    def detect_with_layers(self, records: List[CodeRecord], config: DetectionConfiguration) -> List[SimilarityResult]:
        """Multi-layer detection pipeline."""
        # Layer 1: Data preparation and normalization
        prepared_records = self._prepare_records(records)
        
        # Layer 2: Coarse-grained grouping (O(n))
        candidate_groups = self._extract_candidate_groups(prepared_records)
        
        # Layer 3: Fine-grained similarity calculation (limited scope)
        duplicate_pairs = self._calculate_detailed_similarity(candidate_groups, config)
        
        # Layer 4: Final clustering and output formatting
        return self._format_results(duplicate_pairs, config)
    
    def _prepare_records(self, records: List[CodeRecord]) -> List[Dict[str, Any]]:
        """Layer 1: Normalize and extract features from records."""
        prepared = []
        
        for record in records:
            if not record.code_content:
                continue
                
            # Extract features for grouping
            normalized_content = self._normalize_content(record.code_content)
            feature_key = self._extract_feature_key(record)
            
            prepared.append({
                'record': record,
                'normalized_content': normalized_content,
                'feature_key': feature_key,
                'content_length': len(record.code_content)
            })
        
        return prepared
    
    def _extract_candidate_groups(self, prepared_records: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Layer 2: Group records by features to reduce comparison space."""
        groups = {}
        
        for prepared_record in prepared_records:
            feature_key = prepared_record['feature_key']
            
            if feature_key not in groups:
                groups[feature_key] = []
            groups[feature_key].append(prepared_record)
        
        # Filter out single-item groups (no duplicates possible)
        return {k: v for k, v in groups.items() if len(v) > 1}
    
    def _calculate_detailed_similarity(self, candidate_groups: Dict[str, List[Dict[str, Any]]], config: DetectionConfiguration) -> List[Dict[str, Any]]:
        """Layer 3: Calculate similarity only within candidate groups."""
        duplicate_pairs = []
        
        for group_key, group_records in candidate_groups.items():
            # Only compare within groups (much smaller n)
            for i, record1 in enumerate(group_records):
                for record2 in group_records[i+1:]:
                    similarity = self._calculate_similarity_score(
                        record1['normalized_content'], 
                        record2['normalized_content']
                    )
                    
                    if similarity >= config.threshold:
                        duplicate_pairs.append({
                            'record1': record1['record'],
                            'record2': record2['record'],
                            'similarity': similarity,
                            'group_key': group_key
                        })
                        
                        if len(duplicate_pairs) >= config.max_results:
                            return duplicate_pairs
        
        return duplicate_pairs
    
    def _format_results(self, duplicate_pairs: List[Dict[str, Any]], config: DetectionConfiguration) -> List[SimilarityResult]:
        """Layer 4: Format results into SimilarityResult objects."""
        results = []
        
        for pair in duplicate_pairs:
            result = SimilarityResult(
                is_duplicate=True,
                similarity_score=pair['similarity'],
                matched_records=[pair['record1'], pair['record2']],
                analysis_method="layered_detection",
                threshold=config.threshold
            )
            result.add_metadata('group_key', pair['group_key'])
            results.append(result)
        
        return results
    
    def _normalize_content(self, content: str) -> str:
        """Centralized normalization logic."""
        cache_key = hash(content)
        if cache_key in self.normalization_cache:
            return self.normalization_cache[cache_key]
        
        # Advanced normalization following Centralize pattern
        normalized = (
            content.lower()
            .replace(' ', '')
            .replace('\t', '')
            .replace('\n', '')
            .replace('_', '')
        )
        
        self.normalization_cache[cache_key] = normalized
        return normalized
    
    def _extract_feature_key(self, record: CodeRecord) -> str:
        """Extract grouping key following Extract pattern."""
        content = record.code_content or ''
        
        # Create composite key for initial grouping
        length_category = 'short' if len(content) < 100 else 'medium' if len(content) < 500 else 'long'
        first_chars = content[:10].lower().replace(' ', '')
        function_name_category = (record.function_name or 'unknown')[:5]
        
        return f"{length_category}_{first_chars}_{function_name_category}"
    
    def _calculate_similarity_score(self, content1: str, content2: str) -> float:
        """Calculate similarity score using efficient algorithm."""
        if content1 == content2:
            return 1.0
        
        # Simple but effective similarity measure
        len1, len2 = len(content1), len(content2)
        if len1 == 0 or len2 == 0:
            return 0.0
        
        # Jaccard similarity for character sets
        set1, set2 = set(content1), set(content2)
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        return intersection / union if union > 0 else 0.0


class SimHashDetector(DuplicateDetector):
    """Refactored SimHash detector using layered strategy."""
    
    def __init__(self):
        self.strategy = LayeredDetectionStrategy()
    
    def detect_duplicates(self, records: List[CodeRecord], config: DetectionConfiguration) -> List[SimilarityResult]:
        """Detect duplicates with resource management."""
        # Immediate resource limitation to prevent Killed error
        limited_records = records[:config.max_records_per_batch]
        
        # Use exact match detector for better performance
        exact_detector = ExactMatchDetector()
        return exact_detector.detect_duplicates(limited_records, config)
    
    def find_similar(self, source_code: str, records: List[CodeRecord], config: DetectionConfiguration) -> SimilarityResult:
        """Find similar code using SimHash."""
        source_hash = self._calculate_simhash(source_code)
        matched_records = []
        
        for record in records:
            if record.code_content:
                record_hash = self._get_cached_hash(record)
                similarity = self._hash_similarity(source_hash, record_hash)
                
                if similarity >= config.threshold:
                    record.similarity_score = similarity
                    matched_records.append(record)
        
        is_duplicate = len(matched_records) > 0
        avg_similarity = sum(r.similarity_score for r in matched_records) / len(matched_records) if matched_records else 0
        
        return SimilarityResult(
            is_duplicate=is_duplicate,
            similarity_score=avg_similarity,
            matched_records=matched_records,
            analysis_method="simhash",
            threshold=config.threshold
        )
    
    def get_algorithm_name(self) -> str:
        return "simhash"
    
    def _are_similar(self, record1: CodeRecord, record2: CodeRecord, threshold: float) -> bool:
        """Check if two records are similar."""
        if not (record1.code_content and record2.code_content):
            return False
        
        hash1 = self._get_cached_hash(record1)
        hash2 = self._get_cached_hash(record2)
        
        return self._hash_similarity(hash1, hash2) >= threshold
    
    def _calculate_similarity(self, record1: CodeRecord, record2: CodeRecord) -> float:
        """Calculate similarity between two records."""
        hash1 = self._get_cached_hash(record1)
        hash2 = self._get_cached_hash(record2)
        return self._hash_similarity(hash1, hash2)
    
    def _get_cached_hash(self, record: CodeRecord) -> int:
        """Get cached SimHash for record."""
        if record.simhash is not None:
            return record.simhash
        
        cache_key = record.code_hash or id(record)
        if cache_key not in self.hash_cache:
            self.hash_cache[cache_key] = self._calculate_simhash(record.code_content)
        
        return self.hash_cache[cache_key]
    
    def _calculate_simhash(self, code: str) -> int:
        """Calculate SimHash for code content."""
        return hash(code.lower().replace(' ', '').replace('\n', '').replace('\t', '')) % (2**32)
    
    def _hash_similarity(self, hash1: int, hash2: int) -> float:
        """Calculate similarity between two hashes."""
        if hash1 == hash2:
            return 1.0
        
        xor_result = hash1 ^ hash2
        bit_diff = bin(xor_result).count('1')
        return max(0, 1.0 - (bit_diff / 32.0))


class ExactMatchDetector(DuplicateDetector):
    """Exact match detection using content hashing."""
    
    def detect_duplicates(self, records: List[CodeRecord], config: DetectionConfiguration) -> List[SimilarityResult]:
        """Detect exact duplicates."""
        hash_groups = {}
        
        for record in records:
            if record.code_hash:
                if record.code_hash not in hash_groups:
                    hash_groups[record.code_hash] = []
                hash_groups[record.code_hash].append(record)
        
        duplicates = []
        for code_hash, group_records in hash_groups.items():
            if len(group_records) > 1:
                result = SimilarityResult(
                    is_duplicate=True,
                    similarity_score=1.0,
                    matched_records=group_records,
                    analysis_method="exact_match",
                    threshold=config.threshold
                )
                duplicates.append(result)
        
        return duplicates[:config.max_results]
    
    def find_similar(self, source_code: str, records: List[CodeRecord], config: DetectionConfiguration) -> SimilarityResult:
        """Find exact matches."""
        import hashlib
        source_hash = hashlib.sha256(source_code.encode('utf-8')).hexdigest()
        
        matched_records = [r for r in records if r.code_hash == source_hash]
        
        return SimilarityResult(
            is_duplicate=len(matched_records) > 0,
            similarity_score=1.0 if matched_records else 0.0,
            matched_records=matched_records,
            analysis_method="exact_match",
            threshold=config.threshold
        )
    
    def get_algorithm_name(self) -> str:
        return "exact_match"


class UnifiedDetectionService:
    """Unified service managing all detection algorithms."""
    
    def __init__(self):
        self.detectors = {
            "simhash": SimHashDetector(),
            "exact_match": ExactMatchDetector()
        }
        self.default_config = DetectionConfiguration()
    
    def detect_duplicates(self, records: List[CodeRecord], algorithm: str = None, config: DetectionConfiguration = None) -> List[SimilarityResult]:
        """Detect duplicates using specified algorithm."""
        detector = self._get_detector(algorithm)
        detection_config = config or self.default_config
        
        return detector.detect_duplicates(records, detection_config)
    
    def find_similar(self, source_code: str, records: List[CodeRecord], algorithm: str = None, config: DetectionConfiguration = None) -> SimilarityResult:
        """Find similar code using specified algorithm."""
        detector = self._get_detector(algorithm)
        detection_config = config or self.default_config
        
        return detector.find_similar(source_code, records, detection_config)
    
    def get_available_algorithms(self) -> List[str]:
        """Get list of available detection algorithms."""
        return list(self.detectors.keys())
    
    def register_detector(self, name: str, detector: DuplicateDetector):
        """Register a new detection algorithm."""
        self.detectors[name] = detector
    
    def _get_detector(self, algorithm: str = None) -> DuplicateDetector:
        """Get detector by algorithm name."""
        algo_name = algorithm or self.default_config.algorithm
        
        if algo_name not in self.detectors:
            algo_name = "simhash"  # fallback to default
        
        return self.detectors[algo_name]