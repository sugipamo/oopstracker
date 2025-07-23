"""
Statistics analysis layer for AST SimHash detector.
Handles collecting and analyzing code statistics.
"""

import logging
from typing import Dict, List, Any
from collections import defaultdict

from ..models import CodeRecord
from ..detectors import StatisticsCollector
from ..ast_analyzer import ASTAnalyzer

logger = logging.getLogger(__name__)


class StatisticsAnalysisLayer:
    """Handles statistics collection and analysis."""
    
    def __init__(self):
        """Initialize statistics analysis layer."""
        self.statistics_collector = StatisticsCollector()
        self.analyzer = ASTAnalyzer()
        
    def get_statistics(self, data_layer, hamming_threshold: int = 10) -> Dict:
        """
        Get comprehensive statistics about registered code.
        
        Args:
            data_layer: Data management layer instance
            hamming_threshold: Hamming distance threshold
            
        Returns:
            Dictionary with statistics
        """
        records = data_layer.get_all_records()
        basic_stats = self.statistics_collector.collect_statistics(
            records, hamming_threshold
        )
        
        # Add advanced statistics
        advanced_stats = self._collect_advanced_statistics(data_layer)
        
        return {**basic_stats, **advanced_stats}
    
    def _collect_advanced_statistics(self, data_layer) -> Dict:
        """Collect advanced statistics about the codebase."""
        records = data_layer.get_all_records()
        
        # Group by file
        files_stats = defaultdict(lambda: {
            'functions': 0, 'classes': 0, 'total_lines': 0
        })
        
        # Group by intent category
        intent_stats = defaultdict(int)
        
        # Complexity distribution
        complexity_distribution = defaultdict(int)
        
        for record in records:
            # File statistics
            if record.file_path:
                stats = files_stats[record.file_path]
                if record.code_type == 'function':
                    stats['functions'] += 1
                elif record.code_type == 'class':
                    stats['classes'] += 1
                stats['total_lines'] += (record.end_line - record.start_line + 1)
            
            # Intent statistics
            if record.intent_category:
                intent_stats[record.intent_category] += 1
            
            # Get complexity from code unit
            unit = data_layer.get_unit(record.code_hash)
            if unit and hasattr(unit, 'complexity'):
                complexity_bucket = self._get_complexity_bucket(unit.complexity)
                complexity_distribution[complexity_bucket] += 1
        
        return {
            'file_statistics': dict(files_stats),
            'intent_distribution': dict(intent_stats),
            'complexity_distribution': dict(complexity_distribution),
            'average_file_size': self._calculate_average_file_size(files_stats),
            'code_diversity_score': self._calculate_diversity_score(records)
        }
    
    def _get_complexity_bucket(self, complexity: int) -> str:
        """Categorize complexity into buckets."""
        if complexity <= 5:
            return 'simple'
        elif complexity <= 10:
            return 'moderate'
        elif complexity <= 20:
            return 'complex'
        else:
            return 'very_complex'
    
    def _calculate_average_file_size(self, files_stats: Dict) -> float:
        """Calculate average file size in lines."""
        if not files_stats:
            return 0.0
        
        total_lines = sum(stats['total_lines'] for stats in files_stats.values())
        return round(total_lines / len(files_stats), 2)
    
    def _calculate_diversity_score(self, records: List[CodeRecord]) -> float:
        """
        Calculate code diversity score based on unique patterns.
        Higher score means more diverse codebase.
        """
        if not records:
            return 0.0
        
        # Count unique SimHashes
        unique_simhashes = set()
        for record in records:
            if record.simhash is not None:
                unique_simhashes.add(record.simhash)
        
        # Diversity is ratio of unique patterns to total
        diversity = len(unique_simhashes) / len(records)
        return round(diversity * 100, 2)
    
    def analyze_code_structure(self, source_code: str, 
                               file_path: Any = None) -> Dict:
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
            ],
            "summary": self._generate_structure_summary(units)
        }
    
    def _generate_structure_summary(self, units: List) -> Dict:
        """Generate summary of code structure."""
        if not units:
            return {"message": "No code units found"}
        
        total_lines = sum(u.end_line - u.start_line + 1 for u in units)
        avg_complexity = sum(u.complexity for u in units) / len(units)
        
        return {
            "total_functions": sum(1 for u in units if u.unit_type == 'function'),
            "total_classes": sum(1 for u in units if u.unit_type == 'class'),
            "total_lines": total_lines,
            "average_unit_size": round(total_lines / len(units), 2),
            "average_complexity": round(avg_complexity, 2),
            "intent_coverage": sum(1 for u in units if u.intent_category) / len(units)
        }
    
    def generate_quality_report(self, data_layer) -> Dict:
        """
        Generate a comprehensive code quality report.
        
        Args:
            data_layer: Data management layer instance
            
        Returns:
            Quality report dictionary
        """
        stats = self.get_statistics(data_layer)
        
        # Calculate quality metrics
        quality_metrics = {
            'duplication_level': self._calculate_duplication_level(stats),
            'complexity_score': self._calculate_complexity_score(stats),
            'documentation_score': self._calculate_documentation_score(data_layer),
            'modularity_score': self._calculate_modularity_score(stats)
        }
        
        # Overall quality score (weighted average)
        overall_score = (
            quality_metrics['duplication_level'] * 0.3 +
            quality_metrics['complexity_score'] * 0.3 +
            quality_metrics['documentation_score'] * 0.2 +
            quality_metrics['modularity_score'] * 0.2
        )
        
        return {
            'overall_score': round(overall_score, 2),
            'quality_metrics': quality_metrics,
            'recommendations': self._generate_recommendations(quality_metrics),
            'detailed_statistics': stats
        }
    
    def _calculate_duplication_level(self, stats: Dict) -> float:
        """Calculate duplication level score (0-100, higher is better)."""
        diversity = stats.get('code_diversity_score', 100)
        return diversity  # Already 0-100
    
    def _calculate_complexity_score(self, stats: Dict) -> float:
        """Calculate complexity score (0-100, higher is better)."""
        dist = stats.get('complexity_distribution', {})
        if not dist:
            return 50.0
        
        total = sum(dist.values())
        if total == 0:
            return 50.0
        
        # Weight: simple=100, moderate=75, complex=50, very_complex=25
        weights = {'simple': 100, 'moderate': 75, 'complex': 50, 'very_complex': 25}
        
        score = sum(weights.get(bucket, 0) * count for bucket, count in dist.items())
        return round(score / total, 2)
    
    def _calculate_documentation_score(self, data_layer) -> float:
        """Calculate documentation score based on intent coverage."""
        records = data_layer.get_all_records()
        if not records:
            return 0.0
        
        documented = sum(1 for r in records if r.intent_category)
        return round((documented / len(records)) * 100, 2)
    
    def _calculate_modularity_score(self, stats: Dict) -> float:
        """Calculate modularity score based on file organization."""
        file_stats = stats.get('file_statistics', {})
        if not file_stats:
            return 50.0
        
        # Good modularity: reasonable file sizes, balanced distribution
        avg_size = stats.get('average_file_size', 0)
        
        # Ideal file size is 100-300 lines
        if 100 <= avg_size <= 300:
            size_score = 100
        elif avg_size < 100:
            size_score = avg_size  # Too small
        else:
            size_score = max(0, 100 - (avg_size - 300) / 10)  # Too large
        
        return round(size_score, 2)
    
    def _generate_recommendations(self, metrics: Dict) -> List[str]:
        """Generate recommendations based on quality metrics."""
        recommendations = []
        
        if metrics['duplication_level'] < 70:
            recommendations.append("High code duplication detected. Consider refactoring common patterns.")
        
        if metrics['complexity_score'] < 60:
            recommendations.append("Many complex functions found. Consider breaking them into smaller units.")
        
        if metrics['documentation_score'] < 50:
            recommendations.append("Low intent documentation. Add intent categories to improve code understanding.")
        
        if metrics['modularity_score'] < 60:
            recommendations.append("File sizes are not optimal. Consider reorganizing code structure.")
        
        if not recommendations:
            recommendations.append("Code quality is good! Keep up the excellent work.")
        
        return recommendations