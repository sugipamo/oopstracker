"""
SimHash calculation and BKTree management.
"""

import logging
from typing import Dict, Optional, List

from ...ast_analyzer import CodeUnit
from ...models import CodeRecord
from ...simhash_detector import BKTree

logger = logging.getLogger(__name__)


class SimHashCalculator:
    """
    Manages SimHash calculations and BKTree operations for code similarity.
    """
    
    def __init__(self, hamming_threshold: int = 10):
        """
        Initialize SimHash calculator.
        
        Args:
            hamming_threshold: Maximum Hamming distance for similarity
        """
        self.hamming_threshold = hamming_threshold
        self.bk_tree = BKTree()
        self.code_units: Dict[str, CodeUnit] = {}  # hash -> CodeUnit
        self.records: Dict[str, CodeRecord] = {}   # hash -> CodeRecord
        
    def add_code_unit(self, unit: CodeUnit) -> Optional[CodeRecord]:
        """
        Add a code unit to the BKTree and create a record.
        
        Args:
            unit: The code unit to add
            
        Returns:
            CodeRecord if successfully added, None if duplicate
        """
        if unit.hash in self.code_units:
            logger.debug(f"Code unit already exists: {unit.hash}")
            return None
            
        # Create record first
        record = CodeRecord(
            code_hash=unit.hash,
            file_path=unit.file_path,
            function_name=unit.name,
            code_content=unit.source_code
        )
        
        # Generate simhash for BKTree operations  
        from simhash import Simhash
        simhash_value = Simhash(unit.source_code).value
        
        # Add to BKTree with simhash value
        self.bk_tree.insert(simhash_value, record)
        
        # Store code unit and record
        self.code_units[unit.hash] = unit
        self.records[unit.hash] = record
        
        logger.debug(f"Added code unit: {unit.name} from {unit.file_path}")
        return record
        
    def find_similar_hashes(self, target_hash: str, threshold: Optional[int] = None) -> List[str]:
        """
        Find similar hashes within the threshold.
        
        Args:
            target_hash: The hash to search for
            threshold: Maximum Hamming distance (uses default if None)
            
        Returns:
            List of similar hashes
        """
        threshold = threshold or self.hamming_threshold
        return self.bk_tree.find(target_hash, threshold)
        
    def get_record(self, hash_value: str) -> Optional[CodeRecord]:
        """Get a record by hash."""
        return self.records.get(hash_value)
        
    def get_code_unit(self, hash_value: str) -> Optional[CodeUnit]:
        """Get a code unit by hash."""
        return self.code_units.get(hash_value)
        
    def clear(self):
        """Clear all stored data."""
        self.bk_tree = BKTree()
        self.code_units.clear()
        self.records.clear()
        
    def get_all_records(self) -> List[CodeRecord]:
        """Get all stored records."""
        return list(self.records.values())
        
    def get_statistics(self) -> Dict:
        """Get statistics about stored data."""
        return {
            'total_records': len(self.records),
            'total_units': len(self.code_units),
            'hamming_threshold': self.hamming_threshold
        }