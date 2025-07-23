"""
AST-based code analysis service.
Handles code structure analysis and statistics collection.
"""

import logging
from typing import Dict, List, Optional

from ..ast_analyzer import ASTAnalyzer, CodeUnit
from ..models import CodeRecord
from ..detectors import StatisticsCollector

logger = logging.getLogger(__name__)


class ASTCodeAnalysisService:
    """Service for handling code analysis operations."""
    
    def __init__(self, analyzer: ASTAnalyzer, records: Dict[str, CodeRecord], 
                 code_units: Dict[str, CodeUnit], hamming_threshold: int = 10):
        """
        Initialize code analysis service.
        
        Args:
            analyzer: AST analyzer instance
            records: Shared records dictionary
            code_units: Shared code units dictionary
            hamming_threshold: Maximum Hamming distance for similarity
        """
        self.analyzer = analyzer
        self.records = records
        self.code_units = code_units
        self.hamming_threshold = hamming_threshold
        
        # Initialize components
        self.statistics_collector = StatisticsCollector()
    
    def analyze_code_structure(self, source_code: str, file_path: Optional[str] = None) -> Dict:
        """
        Analyze the structure of given source code.
        
        Args:
            source_code: Python source code to analyze
            file_path: Optional file path for context
            
        Returns:
            Dictionary with analysis results
        """
        units = self.analyzer.extract_units_from_source(source_code)
        
        return {
            "total_units": len(units),
            "units": [
                {
                    "name": unit.name,
                    "type": unit.unit_type,
                    "start_line": unit.start_line,
                    "end_line": unit.end_line,
                    "complexity": unit.complexity,
                    "intent_category": unit.intent_category,
                    "metrics": {
                        "lines": unit.end_line - unit.start_line + 1,
                        "ast_nodes": len(unit.ast_nodes) if hasattr(unit, 'ast_nodes') else 0,
                        "variables": len(unit.variables) if hasattr(unit, 'variables') else 0,
                        "calls": len(unit.calls) if hasattr(unit, 'calls') else 0
                    }
                }
                for unit in units
            ]
        }
    
    def get_statistics(self) -> Dict:
        """
        Get statistics about registered code.
        
        Returns:
            Dictionary with statistics
        """
        return self.statistics_collector.collect_statistics(
            self.records, self.hamming_threshold
        )
    
    def get_all_records(self) -> List[CodeRecord]:
        """
        Get all registered records.
        
        Returns:
            List of all CodeRecord objects
        """
        return list(self.records.values())