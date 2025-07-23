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


class SimHashDetector(DuplicateDetector):
    """SimHash-based duplicate detection."""
    
    def __init__(self):
        self.hash_cache = {}
    
    def detect_duplicates(self, records: List[CodeRecord], config: DetectionConfiguration) -> List[SimilarityResult]:
        """Detect duplicates using SimHash."""
        duplicates = []
        
        for i, record1 in enumerate(records):
            for record2 in records[i+1:]:
                if self._are_similar(record1, record2, config.threshold):
                    result = SimilarityResult(
                        is_duplicate=True,
                        similarity_score=self._calculate_similarity(record1, record2),
                        matched_records=[record1, record2],
                        analysis_method="simhash",
                        threshold=config.threshold
                    )
                    duplicates.append(result)
        
        return duplicates[:config.max_results]
    
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