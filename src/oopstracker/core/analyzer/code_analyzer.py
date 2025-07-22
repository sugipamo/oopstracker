"""
Code structure analysis and statistics.
"""

import logging
from typing import Dict, List, Optional, Set

from ...ast_analyzer import ASTAnalyzer, CodeUnit
from ...models import CodeRecord
from ..simhash import SimHashCalculator

logger = logging.getLogger(__name__)


class CodeAnalyzer:
    """
    Analyzes code structure and provides statistics.
    """
    
    def __init__(self, analyzer: ASTAnalyzer, simhash_calculator: SimHashCalculator):
        """
        Initialize code analyzer.
        
        Args:
            analyzer: AST analyzer instance
            simhash_calculator: SimHash calculator for accessing stored records
        """
        self.analyzer = analyzer
        self.simhash_calculator = simhash_calculator
        
    def analyze_code_structure(self, source_code: str, file_path: Optional[str] = None) -> Dict:
        """
        Analyze code structure without registering.
        
        Args:
            source_code: Python source code
            file_path: Optional file path for context
            
        Returns:
            Dictionary with analysis results
        """
        units = self.analyzer.parse_code(source_code, file_path or "")
        
        analysis = {
            "total_units": len(units),
            "functions": [self._unit_to_dict(u) for u in units if u.type == "function"],
            "classes": [self._unit_to_dict(u) for u in units if u.type == "class"],
            "methods": [self._unit_to_dict(u) for u in units if u.type == "method"]
        }
        
        # Add complexity analysis
        total_complexity = sum(u.complexity_score or 0 for u in units)
        analysis["total_complexity"] = total_complexity
        analysis["average_complexity"] = total_complexity / len(units) if units else 0
        
        # Add dependency analysis
        all_deps: Set[str] = set()
        for unit in units:
            all_deps.update(unit.dependencies or [])
        analysis["dependencies"] = sorted(all_deps)
        
        # Add size metrics
        analysis["total_lines"] = sum(u.line_count or 0 for u in units)
        analysis["largest_unit"] = max((u.line_count or 0 for u in units), default=0)
        
        return analysis
        
    def _unit_to_dict(self, unit: CodeUnit) -> Dict:
        """Convert a code unit to a dictionary for analysis results."""
        return {
            "name": unit.name,
            "type": unit.type,
            "line_number": unit.line_number,
            "line_count": unit.line_count,
            "complexity": unit.complexity_score,
            "dependencies": list(unit.dependencies or [])
        }
        
    def get_statistics(self) -> Dict:
        """
        Get detector statistics.
        
        Returns:
            Dictionary with statistics
        """
        records = self.simhash_calculator.get_all_records()
        
        # Count by type
        function_count = sum(1 for r in records if r.function_name and not r.function_name.startswith("class "))
        class_count = sum(1 for r in records if r.function_name and r.function_name.startswith("class "))
        
        # File statistics
        unique_files = {r.full_path for r in records}
        
        # Size statistics
        total_lines = sum(r.source_code.count('\n') + 1 for r in records)
        avg_lines = total_lines / len(records) if records else 0
        
        # Complexity distribution
        complexity_buckets = {"low": 0, "medium": 0, "high": 0, "very_high": 0}
        
        for record in records:
            unit = self.simhash_calculator.get_code_unit(record.code_hash)
            if unit and unit.complexity_score:
                if unit.complexity_score < 5:
                    complexity_buckets["low"] += 1
                elif unit.complexity_score < 10:
                    complexity_buckets["medium"] += 1
                elif unit.complexity_score < 20:
                    complexity_buckets["high"] += 1
                else:
                    complexity_buckets["very_high"] += 1
        
        return {
            "total_records": len(records),
            "total_units": len(self.simhash_calculator.code_units),
            "function_count": function_count,
            "class_count": class_count,
            "unique_files": len(unique_files),
            "total_lines": total_lines,
            "average_lines_per_unit": avg_lines,
            "complexity_distribution": complexity_buckets,
            "hamming_threshold": self.simhash_calculator.hamming_threshold
        }
        
    def get_file_statistics(self, file_path: str) -> Optional[Dict]:
        """
        Get statistics for a specific file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Dictionary with file statistics or None if file not found
        """
        file_records = [
            r for r in self.simhash_calculator.get_all_records()
            if r.full_path == file_path
        ]
        
        if not file_records:
            return None
            
        file_units = []
        for record in file_records:
            unit = self.simhash_calculator.get_code_unit(record.code_hash)
            if unit:
                file_units.append(unit)
                
        return {
            "file_path": file_path,
            "total_units": len(file_units),
            "functions": sum(1 for u in file_units if u.type == "function"),
            "classes": sum(1 for u in file_units if u.type == "class"),
            "methods": sum(1 for u in file_units if u.type == "method"),
            "total_lines": sum(u.line_count or 0 for u in file_units),
            "total_complexity": sum(u.complexity_score or 0 for u in file_units),
            "average_complexity": sum(u.complexity_score or 0 for u in file_units) / len(file_units) if file_units else 0
        }
        
    def get_complexity_report(self, threshold: int = 10) -> List[Dict]:
        """
        Get report of high-complexity code units.
        
        Args:
            threshold: Minimum complexity score to include
            
        Returns:
            List of high-complexity units sorted by complexity
        """
        high_complexity = []
        
        for record in self.simhash_calculator.get_all_records():
            unit = self.simhash_calculator.get_code_unit(record.code_hash)
            if unit and unit.complexity_score and unit.complexity_score >= threshold:
                high_complexity.append({
                    "name": unit.name,
                    "file": unit.file_path,
                    "line": unit.line_number,
                    "type": unit.type,
                    "complexity": unit.complexity_score,
                    "lines": unit.line_count
                })
                
        # Sort by complexity descending
        high_complexity.sort(key=lambda x: x["complexity"], reverse=True)
        
        return high_complexity