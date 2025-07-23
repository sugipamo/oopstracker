"""
Cluster metadata and history management.
Extracted from function_group_clustering_original.py.
"""

import asyncio
import logging
from typing import Dict, Any, List
from .clustering_models import ClusterSplitResult

logger = logging.getLogger(__name__)


class ClusterMetadataManager:
    """Manages cluster metadata, history, and insights."""
    
    def __init__(self):
        self.cluster_history: List[Dict[str, Any]] = []
        self.split_patterns: Dict[str, tuple] = {}
        self.logger = logger
    
    def record_split_result(self, split_result: ClusterSplitResult):
        """Record split result metadata for learning and history."""
        metadata = {
            'timestamp': asyncio.get_event_loop().time(),
            'original_cluster_id': split_result.original_cluster_id,
            'split_patterns': split_result.split_patterns,
            'group_a_size': len(split_result.group_a.functions),
            'group_b_size': len(split_result.group_b.functions),
            'unmatched_size': len(split_result.unmatched),
            'evaluation_scores': split_result.evaluation_scores,
            'group_a_label': split_result.group_a.label,
            'group_b_label': split_result.group_b.label
        }
        
        self.cluster_history.append({
            'event': 'cluster_split',
            'metadata': metadata
        })
        
        # Store successful split patterns for reuse
        if split_result.evaluation_scores[0] > 0.7 and split_result.evaluation_scores[1] > 0.7:
            pattern_key = f"{split_result.group_a.label}|{split_result.group_b.label}"
            self.split_patterns[pattern_key] = split_result.split_patterns
            self.logger.info(f"Stored successful split pattern: {pattern_key}")
    
    def get_insights(self) -> Dict[str, Any]:
        """Extract insights from clustering history."""
        if not self.cluster_history:
            return {
                'total_operations': 0,
                'successful_patterns': {},
                'average_scores': 0.0
            }
        
        # Calculate statistics
        split_events = [e for e in self.cluster_history if e['event'] == 'cluster_split']
        
        total_scores = []
        pattern_usage = {}
        
        for event in split_events:
            metadata = event['metadata']
            scores = metadata.get('evaluation_scores', [])
            if scores:
                total_scores.extend(scores)
            
            patterns = metadata.get('split_patterns', ())
            if patterns:
                pattern_str = str(patterns)
                pattern_usage[pattern_str] = pattern_usage.get(pattern_str, 0) + 1
        
        avg_score = sum(total_scores) / len(total_scores) if total_scores else 0.0
        
        # Find most successful patterns
        successful_patterns = {}
        for pattern_key, patterns in self.split_patterns.items():
            usage_count = pattern_usage.get(str(patterns), 0)
            if usage_count > 0:
                successful_patterns[pattern_key] = {
                    'patterns': patterns,
                    'usage_count': usage_count
                }
        
        return {
            'total_operations': len(self.cluster_history),
            'total_splits': len(split_events),
            'successful_patterns': successful_patterns,
            'average_evaluation_score': avg_score,
            'stored_pattern_count': len(self.split_patterns),
            'pattern_usage_stats': pattern_usage
        }
    
    def get_suggested_patterns(self, cluster_label: str) -> List[tuple]:
        """Get suggested split patterns based on history."""
        suggestions = []
        
        # Look for patterns used with similar labels
        for pattern_key, patterns in self.split_patterns.items():
            labels = pattern_key.split('|')
            # Check if any label word appears in the cluster label
            for label in labels:
                if any(word.lower() in cluster_label.lower() 
                      for word in label.split() if len(word) > 3):
                    suggestions.append(patterns)
                    break
        
        return suggestions[:3]  # Return top 3 suggestions