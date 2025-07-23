"""Metadata recording for clustering operations."""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from collections import defaultdict

from ...clustering_models import ClusterSplitResult, FunctionGroup


class MetadataRecorder:
    """Record and manage metadata for clustering operations."""
    
    def __init__(self):
        """Initialize the metadata recorder."""
        self.logger = logging.getLogger(__name__)
        self.clustering_history: List[Dict[str, Any]] = []
        self.split_history: List[Dict[str, Any]] = []
        self.performance_metrics: Dict[str, List[float]] = defaultdict(list)
        
    def record_clustering_operation(
        self,
        operation_type: str,
        input_count: int,
        output_count: int,
        strategy: str,
        duration: float,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Record a clustering operation.
        
        Args:
            operation_type: Type of operation (e.g., 'initial_clustering', 'refinement')
            input_count: Number of input functions
            output_count: Number of output clusters
            strategy: Clustering strategy used
            duration: Operation duration in seconds
            metadata: Additional metadata
        """
        record = {
            'timestamp': datetime.now().isoformat(),
            'operation_type': operation_type,
            'input_count': input_count,
            'output_count': output_count,
            'strategy': strategy,
            'duration': duration,
            'compression_ratio': input_count / output_count if output_count > 0 else 0,
            'metadata': metadata or {}
        }
        
        self.clustering_history.append(record)
        self.performance_metrics[f"{operation_type}_duration"].append(duration)
        
        self.logger.info(
            f"Recorded {operation_type}: {input_count} functions -> "
            f"{output_count} clusters using {strategy} (took {duration:.2f}s)"
        )
    
    def record_split_operation(self, split_result: ClusterSplitResult):
        """Record a cluster split operation.
        
        Args:
            split_result: The split result to record
        """
        original_size = len(split_result.original_cluster.functions)
        
        record = {
            'timestamp': datetime.now().isoformat(),
            'cluster_id': split_result.original_cluster.group_id,
            'cluster_label': split_result.original_cluster.label,
            'original_size': original_size,
            'group_a_size': len(split_result.group_a.functions) if split_result.group_a else 0,
            'group_b_size': len(split_result.group_b.functions) if split_result.group_b else 0,
            'unmatched_size': len(split_result.unmatched_group.functions) if split_result.unmatched_group else 0,
            'pattern_a': split_result.pattern_a,
            'pattern_b': split_result.pattern_b,
            'split_metadata': split_result.metadata
        }
        
        self.split_history.append(record)
        
        # Calculate and record split effectiveness
        matched = record['group_a_size'] + record['group_b_size']
        effectiveness = matched / original_size if original_size > 0 else 0
        self.performance_metrics['split_effectiveness'].append(effectiveness)
        
        self.logger.info(
            f"Recorded split of '{record['cluster_label']}': "
            f"{original_size} -> A:{record['group_a_size']}, "
            f"B:{record['group_b_size']}, Unmatched:{record['unmatched_size']}"
        )
    
    def record_cluster_quality(self, clusters: List[FunctionGroup]):
        """Record quality metrics for a set of clusters.
        
        Args:
            clusters: List of function groups to analyze
        """
        if not clusters:
            return
        
        # Calculate quality metrics
        sizes = [len(c.functions) for c in clusters]
        confidences = [c.confidence for c in clusters]
        
        quality_record = {
            'timestamp': datetime.now().isoformat(),
            'cluster_count': len(clusters),
            'total_functions': sum(sizes),
            'size_distribution': {
                'min': min(sizes),
                'max': max(sizes),
                'avg': sum(sizes) / len(sizes),
                'median': sorted(sizes)[len(sizes) // 2]
            },
            'confidence_distribution': {
                'min': min(confidences),
                'max': max(confidences),
                'avg': sum(confidences) / len(confidences)
            },
            'size_variance': self._calculate_variance(sizes),
            'balanced_score': self._calculate_balance_score(sizes)
        }
        
        self.clustering_history.append({
            'type': 'quality_snapshot',
            **quality_record
        })
        
        self.logger.info(
            f"Quality snapshot: {quality_record['cluster_count']} clusters, "
            f"avg size: {quality_record['size_distribution']['avg']:.1f}, "
            f"avg confidence: {quality_record['confidence_distribution']['avg']:.2f}"
        )
    
    def get_operation_summary(self) -> Dict[str, Any]:
        """Get a summary of all recorded operations.
        
        Returns:
            Summary dictionary with statistics
        """
        summary = {
            'total_clustering_operations': len([h for h in self.clustering_history if h.get('operation_type')]),
            'total_split_operations': len(self.split_history),
            'clustering_strategies_used': list(set(h.get('strategy', '') for h in self.clustering_history if h.get('strategy'))),
            'performance_stats': {}
        }
        
        # Calculate performance statistics
        for metric_name, values in self.performance_metrics.items():
            if values:
                summary['performance_stats'][metric_name] = {
                    'count': len(values),
                    'min': min(values),
                    'max': max(values),
                    'avg': sum(values) / len(values)
                }
        
        # Calculate clustering effectiveness
        if self.clustering_history:
            compression_ratios = [
                h.get('compression_ratio', 0) 
                for h in self.clustering_history 
                if h.get('compression_ratio')
            ]
            if compression_ratios:
                summary['avg_compression_ratio'] = sum(compression_ratios) / len(compression_ratios)
        
        # Calculate split effectiveness
        if self.split_history:
            split_effectiveness = []
            for split in self.split_history:
                total = split['original_size']
                matched = split['group_a_size'] + split['group_b_size']
                if total > 0:
                    split_effectiveness.append(matched / total)
            
            if split_effectiveness:
                summary['avg_split_effectiveness'] = sum(split_effectiveness) / len(split_effectiveness)
        
        return summary
    
    def get_clustering_timeline(self) -> List[Dict[str, Any]]:
        """Get a timeline of clustering operations.
        
        Returns:
            List of operations sorted by timestamp
        """
        # Combine all operations
        all_operations = []
        
        # Add clustering operations
        for op in self.clustering_history:
            all_operations.append({
                'type': 'clustering',
                'timestamp': op.get('timestamp'),
                'description': f"{op.get('operation_type', 'clustering')} with {op.get('strategy', 'unknown')}",
                'details': op
            })
        
        # Add split operations
        for op in self.split_history:
            all_operations.append({
                'type': 'split',
                'timestamp': op.get('timestamp'),
                'description': f"Split '{op.get('cluster_label', 'unknown')}'",
                'details': op
            })
        
        # Sort by timestamp
        all_operations.sort(key=lambda x: x.get('timestamp', ''))
        
        return all_operations
    
    def export_metadata(self) -> Dict[str, Any]:
        """Export all metadata for persistence or analysis.
        
        Returns:
            Complete metadata dictionary
        """
        return {
            'clustering_history': self.clustering_history,
            'split_history': self.split_history,
            'performance_metrics': dict(self.performance_metrics),
            'summary': self.get_operation_summary(),
            'export_timestamp': datetime.now().isoformat()
        }
    
    def import_metadata(self, data: Dict[str, Any]):
        """Import metadata from a previous session.
        
        Args:
            data: Metadata dictionary to import
        """
        self.clustering_history = data.get('clustering_history', [])
        self.split_history = data.get('split_history', [])
        
        # Reconstruct performance metrics
        self.performance_metrics.clear()
        for metric_name, values in data.get('performance_metrics', {}).items():
            self.performance_metrics[metric_name] = values
        
        self.logger.info(
            f"Imported metadata: {len(self.clustering_history)} clustering ops, "
            f"{len(self.split_history)} split ops"
        )
    
    def _calculate_variance(self, values: List[float]) -> float:
        """Calculate variance of a list of values.
        
        Args:
            values: List of numeric values
            
        Returns:
            Variance
        """
        if not values:
            return 0.0
        
        mean = sum(values) / len(values)
        return sum((x - mean) ** 2 for x in values) / len(values)
    
    def _calculate_balance_score(self, sizes: List[int]) -> float:
        """Calculate how balanced the cluster sizes are.
        
        Args:
            sizes: List of cluster sizes
            
        Returns:
            Balance score (0-1, where 1 is perfectly balanced)
        """
        if not sizes or len(sizes) == 1:
            return 1.0
        
        # Calculate coefficient of variation
        mean = sum(sizes) / len(sizes)
        if mean == 0:
            return 0.0
        
        std_dev = (self._calculate_variance(sizes) ** 0.5)
        cv = std_dev / mean
        
        # Convert to 0-1 score (lower CV is better)
        # CV of 0 = perfect balance (score 1)
        # CV of 1 or higher = poor balance (score approaches 0)
        return max(0.0, 1.0 - cv)