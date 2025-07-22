"""
Statistics collector for code analysis.

This module handles collection and reporting of code statistics.
"""

from typing import Dict, List, Any

from ..models import CodeRecord


class StatisticsCollector:
    """Collects and reports statistics about registered code."""
    
    def collect_statistics(
        self, 
        records: Dict[str, CodeRecord],
        hamming_threshold: int
    ) -> Dict[str, Any]:
        """
        Collect statistics about registered code.
        
        Args:
            records: Dictionary of hash to CodeRecord
            hamming_threshold: Current hamming threshold setting
            
        Returns:
            Dictionary containing statistics
        """
        if not records:
            return {
                "total_units": 0,
                "files": 0,
                "functions": 0,
                "classes": 0,
                "modules": 0,
                "hamming_threshold": hamming_threshold,
                "memory_loaded": 0
            }
        
        # Count by type
        function_count = sum(1 for r in records.values() if r.code_type == "function")
        class_count = sum(1 for r in records.values() if r.code_type == "class")
        module_count = sum(1 for r in records.values() if r.code_type == "module")
        
        # Get unique files
        files = {r.file_path for r in records.values() if r.file_path}
        
        return {
            "total_units": len(records),
            "files": len(files),
            "functions": function_count,
            "classes": class_count,
            "modules": module_count,
            "hamming_threshold": hamming_threshold,
            "memory_loaded": len(records)
        }
    
    def generate_type_distribution(self, records: Dict[str, CodeRecord]) -> Dict[str, int]:
        """
        Generate distribution of code types.
        
        Args:
            records: Dictionary of hash to CodeRecord
            
        Returns:
            Dictionary mapping code type to count
        """
        distribution = {}
        for record in records.values():
            code_type = record.code_type
            distribution[code_type] = distribution.get(code_type, 0) + 1
        return distribution
    
    def generate_file_statistics(self, records: Dict[str, CodeRecord]) -> Dict[str, Dict[str, int]]:
        """
        Generate per-file statistics.
        
        Args:
            records: Dictionary of hash to CodeRecord
            
        Returns:
            Dictionary mapping file path to statistics
        """
        file_stats = {}
        
        for record in records.values():
            if not record.file_path:
                continue
                
            if record.file_path not in file_stats:
                file_stats[record.file_path] = {
                    "functions": 0,
                    "classes": 0,
                    "modules": 0,
                    "total": 0
                }
            
            file_stats[record.file_path]["total"] += 1
            
            if record.code_type == "function":
                file_stats[record.file_path]["functions"] += 1
            elif record.code_type == "class":
                file_stats[record.file_path]["classes"] += 1
            elif record.code_type == "module":
                file_stats[record.file_path]["modules"] += 1
        
        return file_stats
    
    def get_largest_files(
        self, 
        records: Dict[str, CodeRecord], 
        top_n: int = 10
    ) -> List[tuple[str, int]]:
        """
        Get files with most code units.
        
        Args:
            records: Dictionary of hash to CodeRecord
            top_n: Number of top files to return
            
        Returns:
            List of (file_path, unit_count) tuples
        """
        file_counts = {}
        
        for record in records.values():
            if record.file_path:
                file_counts[record.file_path] = file_counts.get(record.file_path, 0) + 1
        
        # Sort by count descending
        sorted_files = sorted(file_counts.items(), key=lambda x: x[1], reverse=True)
        
        return sorted_files[:top_n]