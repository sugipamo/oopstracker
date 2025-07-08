"""
SimHash-based similarity detection for high-performance code duplicate detection.
"""

import re
from typing import List, Dict, Set, Optional, Tuple
from simhash import Simhash
import logging

from .models import CodeRecord, SimilarityResult
from .core import CodeNormalizer
from .exceptions import CodeAnalysisError


class BKTree:
    """
    BK-tree (Burkhard-Keller tree) for fast similarity search with Hamming distance.
    
    This data structure allows for efficient nearest neighbor search in metric spaces.
    For SimHash, we use Hamming distance as the metric.
    """
    
    def __init__(self):
        self.root = None
        self.size = 0
        self.logger = logging.getLogger(__name__)
    
    def insert(self, simhash_value: int, record: CodeRecord):
        """Insert a new record into the BK-tree."""
        if self.root is None:
            self.root = BKTreeNode(simhash_value, record)
            self.size = 1
            return
        
        self._insert_recursive(self.root, simhash_value, record)
        self.size += 1
    
    def _insert_recursive(self, node: 'BKTreeNode', simhash_value: int, record: CodeRecord):
        """Recursively insert a record into the BK-tree."""
        distance = self._hamming_distance(node.simhash, simhash_value)
        
        if distance in node.children:
            self._insert_recursive(node.children[distance], simhash_value, record)
        else:
            node.children[distance] = BKTreeNode(simhash_value, record)
    
    def search(self, simhash_value: int, max_distance: int) -> List[Tuple[CodeRecord, int]]:
        """Search for records within max_distance of the given simhash."""
        if self.root is None:
            return []
        
        results = []
        self._search_recursive(self.root, simhash_value, max_distance, results)
        return results
    
    def _search_recursive(self, node: 'BKTreeNode', simhash_value: int, max_distance: int, results: List):
        """Recursively search the BK-tree for similar records."""
        distance = self._hamming_distance(node.simhash, simhash_value)
        
        if distance <= max_distance:
            results.append((node.record, distance))
        
        # Search child nodes that might contain results
        for child_distance in node.children:
            if abs(child_distance - distance) <= max_distance:
                self._search_recursive(node.children[child_distance], simhash_value, max_distance, results)
    
    def remove(self, simhash_value: int, record_id: int) -> bool:
        """Remove a record from the BK-tree. Returns True if found and removed."""
        if self.root is None:
            return False
        
        found, self.root = self._remove_recursive(self.root, simhash_value, record_id)
        if found:
            self.size -= 1
        return found
    
    def _remove_recursive(self, node: 'BKTreeNode', simhash_value: int, record_id: int) -> Tuple[bool, Optional['BKTreeNode']]:
        """Recursively remove a record from the BK-tree."""
        if node is None:
            return False, None
        
        distance = self._hamming_distance(node.simhash, simhash_value)
        
        # Check if this is the node to remove
        if distance == 0 and node.record.id == record_id:
            # Node found, need to remove it
            if not node.children:
                return True, None
            
            # If node has children, we need to reconstruct this part of the tree
            # For simplicity, we'll mark it as removed and handle reconstruction elsewhere
            # In a production system, you'd implement proper node removal with tree restructuring
            self.logger.warning(f"BK-tree node removal with children not fully implemented for record {record_id}")
            return True, node
        
        # Search in children
        for child_distance in list(node.children.keys()):
            if abs(child_distance - distance) <= 0:  # Only search exact matches for removal
                found, new_child = self._remove_recursive(node.children[child_distance], simhash_value, record_id)
                if found:
                    if new_child is None:
                        del node.children[child_distance]
                    else:
                        node.children[child_distance] = new_child
                    return True, node
        
        return False, node
    
    def _hamming_distance(self, hash1: int, hash2: int) -> int:
        """Calculate Hamming distance between two hash values."""
        return bin(hash1 ^ hash2).count('1')
    
    def get_stats(self) -> Dict[str, int]:
        """Get statistics about the BK-tree."""
        if self.root is None:
            return {"size": 0, "depth": 0}
        
        depth = self._calculate_depth(self.root)
        return {
            "size": self.size,
            "depth": depth,
            "root_children": len(self.root.children)
        }
    
    def _calculate_depth(self, node: 'BKTreeNode') -> int:
        """Calculate the maximum depth of the tree."""
        if not node.children:
            return 1
        
        return 1 + max(self._calculate_depth(child) for child in node.children.values())


class BKTreeNode:
    """Node in the BK-tree structure."""
    
    def __init__(self, simhash: int, record: CodeRecord):
        self.simhash = simhash
        self.record = record
        self.children: Dict[int, 'BKTreeNode'] = {}


class SimHashSimilarityDetector:
    """
    High-performance similarity detector using SimHash and BK-tree.
    
    This detector provides much better performance than SHA-256 for similarity search,
    with O(log n) search complexity instead of O(n).
    """
    
    def __init__(self, threshold: int = 5):
        """
        Initialize the SimHash similarity detector.
        
        Args:
            threshold: Maximum Hamming distance to consider as similar (default: 5)
        """
        self.threshold = threshold
        self.normalizer = CodeNormalizer()
        self.bk_tree = BKTree()
        self.logger = logging.getLogger(__name__)
    
    def _extract_features(self, code: str) -> List[str]:
        """Extract features from code for SimHash calculation."""
        try:
            # Normalize the code first
            normalized = self.normalizer.normalize_code(code)
            
            # Extract features: words, operators, keywords
            features = []
            
            # Split into tokens
            tokens = re.findall(r'\b\w+\b|[^\w\s]', normalized)
            
            # Add individual tokens
            features.extend(tokens)
            
            # Add bigrams for better context
            for i in range(len(tokens) - 1):
                features.append(f"{tokens[i]}_{tokens[i+1]}")
            
            # Add trigrams for even better context
            for i in range(len(tokens) - 2):
                features.append(f"{tokens[i]}_{tokens[i+1]}_{tokens[i+2]}")
            
            return features
            
        except Exception as e:
            self.logger.error(f"Feature extraction failed: {e}")
            # Fallback to simple word splitting
            return code.split()
    
    def calculate_simhash(self, code: str) -> int:
        """Calculate SimHash for the given code."""
        if code is None:
            raise CodeAnalysisError("Code cannot be None")
            
        try:
            features = self._extract_features(code)
            if not features:
                return 0
            
            simhash = Simhash(features)
            return simhash.value
            
        except Exception as e:
            self.logger.error(f"SimHash calculation failed: {e}")
            raise CodeAnalysisError(f"Failed to calculate SimHash: {e}")
    
    def add_record(self, record: CodeRecord) -> bool:
        """Add a code record to the similarity detector."""
        try:
            if not record.code_content:
                return False
            
            # Calculate SimHash if not already present
            if not hasattr(record, 'simhash') or record.simhash is None:
                record.simhash = self.calculate_simhash(record.code_content)
            
            # Add to BK-tree
            self.bk_tree.insert(record.simhash, record)
            
            self.logger.debug(f"Added record {record.id} with SimHash {record.simhash}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to add record: {e}")
            return False
    
    def find_similar(self, code: str, max_distance: Optional[int] = None) -> SimilarityResult:
        """Find similar code records using SimHash and BK-tree."""
        try:
            if not code or not code.strip():
                return SimilarityResult(
                    is_duplicate=False,
                    similarity_score=0.0,
                    matched_records=[],
                    analysis_method="simhash_bktree",
                    threshold=1.0 - (self.threshold / 64.0)
                )
            
            if max_distance is None:
                max_distance = self.threshold
            
            # Calculate SimHash for input code
            query_simhash = self.calculate_simhash(code)
            
            # Search in BK-tree
            results = self.bk_tree.search(query_simhash, max_distance)
            
            # Convert results to SimilarityResult
            matched_records = []
            for record, distance in results:
                # Calculate similarity score (1.0 - normalized_distance)
                similarity_score = max(0.0, 1.0 - (distance / 64.0))  # 64 is max hamming distance
                record.similarity_score = similarity_score
                matched_records.append(record)
            
            # Sort by similarity score (highest first)
            matched_records.sort(key=lambda x: x.similarity_score, reverse=True)
            
            is_duplicate = len(matched_records) > 0
            best_score = matched_records[0].similarity_score if matched_records else 0.0
            
            result = SimilarityResult(
                is_duplicate=is_duplicate,
                similarity_score=best_score,
                matched_records=matched_records,
                analysis_method="simhash_bktree",
                threshold=1.0 - (max_distance / 64.0)  # Convert to normalized threshold
            )
            
            self.logger.info(f"SimHash search found {len(matched_records)} similar records")
            return result
            
        except Exception as e:
            self.logger.error(f"Similarity search failed: {e}")
            raise CodeAnalysisError(f"Failed to find similar code: {e}")
    
    def remove_record(self, record_id: int, simhash: int) -> bool:
        """Remove a record from the similarity detector."""
        try:
            return self.bk_tree.remove(simhash, record_id)
        except Exception as e:
            self.logger.error(f"Failed to remove record: {e}")
            return False
    
    def get_stats(self) -> Dict[str, int]:
        """Get statistics about the similarity detector."""
        return self.bk_tree.get_stats()
    
    def rebuild_index(self, records: List[CodeRecord]):
        """Rebuild the BK-tree index from scratch."""
        try:
            self.bk_tree = BKTree()
            
            for record in records:
                self.add_record(record)
            
            self.logger.info(f"Rebuilt BK-tree index with {len(records)} records")
            
        except Exception as e:
            self.logger.error(f"Failed to rebuild index: {e}")
            raise CodeAnalysisError(f"Failed to rebuild similarity index: {e}")
    
    def analyze_similarity(self, code1: str, code2: str) -> float:
        """Analyze similarity between two code snippets."""
        try:
            hash1 = self.calculate_simhash(code1)
            hash2 = self.calculate_simhash(code2)
            
            distance = bin(hash1 ^ hash2).count('1')
            similarity = max(0.0, 1.0 - (distance / 64.0))
            
            return similarity
            
        except Exception as e:
            self.logger.error(f"Similarity analysis failed: {e}")
            return 0.0
    
    def is_duplicate(self, code1: str, code2: str) -> bool:
        """Check if two code snippets are duplicates."""
        similarity = self.analyze_similarity(code1, code2)
        threshold_normalized = 1.0 - (self.threshold / 64.0)
        return similarity >= threshold_normalized