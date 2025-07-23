"""Generate insights from clustering metadata."""

import logging
from typing import Dict, Any, List, Optional, Tuple
from collections import Counter, defaultdict

from ...clustering_models import FunctionGroup


class InsightGenerator:
    """Generate actionable insights from clustering data."""
    
    def __init__(self):
        """Initialize the insight generator."""
        self.logger = logging.getLogger(__name__)
        
    def generate_insights(
        self,
        clusters: List[FunctionGroup],
        metadata_recorder=None
    ) -> Dict[str, Any]:
        """Generate comprehensive insights from clustering results.
        
        Args:
            clusters: List of function groups
            metadata_recorder: Optional metadata recorder for historical data
            
        Returns:
            Dictionary of insights
        """
        insights = {
            'cluster_analysis': self._analyze_clusters(clusters),
            'patterns': self._identify_patterns(clusters),
            'recommendations': self._generate_recommendations(clusters),
            'quality_assessment': self._assess_quality(clusters)
        }
        
        # Add historical insights if metadata is available
        if metadata_recorder:
            insights['historical_trends'] = self._analyze_historical_trends(metadata_recorder)
        
        return insights
    
    def _analyze_clusters(self, clusters: List[FunctionGroup]) -> Dict[str, Any]:
        """Analyze cluster characteristics.
        
        Args:
            clusters: List of function groups
            
        Returns:
            Analysis results
        """
        if not clusters:
            return {'status': 'no_clusters'}
        
        # Basic statistics
        sizes = [len(c.functions) for c in clusters]
        confidences = [c.confidence for c in clusters]
        
        analysis = {
            'total_clusters': len(clusters),
            'total_functions': sum(sizes),
            'size_distribution': {
                'smallest': min(sizes),
                'largest': max(sizes),
                'average': sum(sizes) / len(sizes),
                'median': sorted(sizes)[len(sizes) // 2]
            },
            'confidence_analysis': {
                'lowest': min(confidences),
                'highest': max(confidences),
                'average': sum(confidences) / len(confidences),
                'low_confidence_clusters': sum(1 for c in confidences if c < 0.6)
            },
            'clustering_strategies': self._count_strategies(clusters),
            'size_categories': self._categorize_sizes(sizes)
        }
        
        # Identify outliers
        avg_size = analysis['size_distribution']['average']
        analysis['outliers'] = {
            'oversized': [
                {'id': c.group_id, 'label': c.label, 'size': len(c.functions)}
                for c in clusters
                if len(c.functions) > avg_size * 2
            ],
            'undersized': [
                {'id': c.group_id, 'label': c.label, 'size': len(c.functions)}
                for c in clusters
                if len(c.functions) < avg_size * 0.5
            ]
        }
        
        return analysis
    
    def _identify_patterns(self, clusters: List[FunctionGroup]) -> Dict[str, Any]:
        """Identify patterns in the clustering results.
        
        Args:
            clusters: List of function groups
            
        Returns:
            Identified patterns
        """
        patterns = {
            'naming_patterns': self._analyze_naming_patterns(clusters),
            'structural_patterns': self._analyze_structural_patterns(clusters),
            'relationship_patterns': self._analyze_relationships(clusters)
        }
        
        return patterns
    
    def _analyze_naming_patterns(self, clusters: List[FunctionGroup]) -> Dict[str, Any]:
        """Analyze naming patterns across clusters.
        
        Args:
            clusters: List of function groups
            
        Returns:
            Naming pattern analysis
        """
        # Collect all function names
        all_names = []
        for cluster in clusters:
            all_names.extend([f['name'] for f in cluster.functions])
        
        # Analyze prefixes
        prefix_counter = Counter()
        suffix_counter = Counter()
        
        for name in all_names:
            parts = name.split('_')
            if len(parts) > 1:
                prefix_counter[parts[0]] += 1
                suffix_counter[parts[-1]] += 1
        
        # Find common patterns
        common_prefixes = [
            {'prefix': prefix, 'count': count, 'percentage': count / len(all_names) * 100}
            for prefix, count in prefix_counter.most_common(10)
            if count > len(all_names) * 0.05  # At least 5% of functions
        ]
        
        common_suffixes = [
            {'suffix': suffix, 'count': count, 'percentage': count / len(all_names) * 100}
            for suffix, count in suffix_counter.most_common(10)
            if count > len(all_names) * 0.05
        ]
        
        return {
            'total_functions': len(all_names),
            'common_prefixes': common_prefixes,
            'common_suffixes': common_suffixes,
            'naming_consistency': self._calculate_naming_consistency(all_names)
        }
    
    def _analyze_structural_patterns(self, clusters: List[FunctionGroup]) -> Dict[str, Any]:
        """Analyze structural patterns in clusters.
        
        Args:
            clusters: List of function groups
            
        Returns:
            Structural pattern analysis
        """
        patterns = defaultdict(int)
        
        for cluster in clusters:
            # Analyze metadata for patterns
            metadata = cluster.metadata
            
            # Clustering strategy patterns
            strategy = metadata.get('clustering_strategy', 'unknown')
            patterns[f'strategy_{strategy}'] += 1
            
            # Size patterns
            size = len(cluster.functions)
            if size < 5:
                patterns['small_clusters'] += 1
            elif size < 15:
                patterns['medium_clusters'] += 1
            else:
                patterns['large_clusters'] += 1
            
            # Confidence patterns
            if cluster.confidence < 0.6:
                patterns['low_confidence'] += 1
            elif cluster.confidence > 0.85:
                patterns['high_confidence'] += 1
        
        return dict(patterns)
    
    def _analyze_relationships(self, clusters: List[FunctionGroup]) -> Dict[str, Any]:
        """Analyze relationships between clusters.
        
        Args:
            clusters: List of function groups
            
        Returns:
            Relationship analysis
        """
        relationships = {
            'potential_merges': [],
            'potential_splits': [],
            'related_clusters': []
        }
        
        # Find clusters that might be merged
        for i, cluster1 in enumerate(clusters):
            for j, cluster2 in enumerate(clusters[i+1:], i+1):
                similarity = self._calculate_cluster_similarity(cluster1, cluster2)
                
                if similarity > 0.7:
                    relationships['potential_merges'].append({
                        'cluster1': {'id': cluster1.group_id, 'label': cluster1.label},
                        'cluster2': {'id': cluster2.group_id, 'label': cluster2.label},
                        'similarity': similarity
                    })
        
        # Find clusters that might need splitting
        for cluster in clusters:
            if len(cluster.functions) > 20 or cluster.confidence < 0.6:
                relationships['potential_splits'].append({
                    'id': cluster.group_id,
                    'label': cluster.label,
                    'size': len(cluster.functions),
                    'confidence': cluster.confidence,
                    'reason': 'oversized' if len(cluster.functions) > 20 else 'low_confidence'
                })
        
        return relationships
    
    def _generate_recommendations(self, clusters: List[FunctionGroup]) -> List[Dict[str, Any]]:
        """Generate actionable recommendations.
        
        Args:
            clusters: List of function groups
            
        Returns:
            List of recommendations
        """
        recommendations = []
        
        # Analyze cluster quality
        sizes = [len(c.functions) for c in clusters]
        avg_size = sum(sizes) / len(sizes) if sizes else 0
        
        # Recommendation for oversized clusters
        oversized = [c for c in clusters if len(c.functions) > avg_size * 2]
        if oversized:
            recommendations.append({
                'type': 'split_recommendation',
                'priority': 'high',
                'message': f"Consider splitting {len(oversized)} oversized clusters",
                'clusters': [{'id': c.group_id, 'label': c.label, 'size': len(c.functions)} for c in oversized]
            })
        
        # Recommendation for low confidence clusters
        low_confidence = [c for c in clusters if c.confidence < 0.6]
        if low_confidence:
            recommendations.append({
                'type': 'refinement_recommendation',
                'priority': 'medium',
                'message': f"Review {len(low_confidence)} low-confidence clusters",
                'clusters': [{'id': c.group_id, 'label': c.label, 'confidence': c.confidence} for c in low_confidence]
            })
        
        # Recommendation for small clusters
        small_clusters = [c for c in clusters if len(c.functions) < 3]
        if len(small_clusters) > len(clusters) * 0.2:
            recommendations.append({
                'type': 'merge_recommendation',
                'priority': 'low',
                'message': f"Consider merging {len(small_clusters)} small clusters",
                'details': f"{len(small_clusters) / len(clusters) * 100:.1f}% of clusters have fewer than 3 functions"
            })
        
        # Strategy recommendations
        strategy_counts = Counter(c.metadata.get('clustering_strategy', 'unknown') for c in clusters)
        if len(strategy_counts) == 1:
            recommendations.append({
                'type': 'strategy_recommendation',
                'priority': 'low',
                'message': "Consider using hybrid clustering for better results",
                'current_strategy': list(strategy_counts.keys())[0]
            })
        
        return recommendations
    
    def _assess_quality(self, clusters: List[FunctionGroup]) -> Dict[str, Any]:
        """Assess overall clustering quality.
        
        Args:
            clusters: List of function groups
            
        Returns:
            Quality assessment
        """
        if not clusters:
            return {'overall_score': 0, 'status': 'no_clusters'}
        
        # Calculate quality metrics
        sizes = [len(c.functions) for c in clusters]
        confidences = [c.confidence for c in clusters]
        
        # Size balance score (0-1)
        size_variance = self._calculate_variance(sizes)
        size_balance = 1 / (1 + size_variance / (sum(sizes) / len(sizes)) ** 2)
        
        # Confidence score (average confidence)
        confidence_score = sum(confidences) / len(confidences)
        
        # Coverage score (how many functions are in reasonably sized clusters)
        total_functions = sum(sizes)
        well_sized_functions = sum(
            size for size in sizes 
            if 3 <= size <= 20
        )
        coverage_score = well_sized_functions / total_functions if total_functions > 0 else 0
        
        # Overall score (weighted average)
        overall_score = (
            size_balance * 0.3 +
            confidence_score * 0.4 +
            coverage_score * 0.3
        )
        
        assessment = {
            'overall_score': overall_score,
            'components': {
                'size_balance': size_balance,
                'confidence_score': confidence_score,
                'coverage_score': coverage_score
            },
            'interpretation': self._interpret_quality_score(overall_score),
            'detailed_metrics': {
                'avg_cluster_size': sum(sizes) / len(sizes),
                'size_std_dev': size_variance ** 0.5,
                'confidence_range': max(confidences) - min(confidences),
                'well_sized_percentage': well_sized_functions / total_functions * 100 if total_functions > 0 else 0
            }
        }
        
        return assessment
    
    def _analyze_historical_trends(self, metadata_recorder) -> Dict[str, Any]:
        """Analyze historical trends from metadata.
        
        Args:
            metadata_recorder: Metadata recorder instance
            
        Returns:
            Historical trend analysis
        """
        summary = metadata_recorder.get_operation_summary()
        timeline = metadata_recorder.get_clustering_timeline()
        
        trends = {
            'operation_count': summary.get('total_clustering_operations', 0),
            'split_count': summary.get('total_split_operations', 0),
            'strategies_used': summary.get('clustering_strategies_used', []),
            'performance_trends': {}
        }
        
        # Analyze performance trends
        perf_stats = summary.get('performance_stats', {})
        for metric, stats in perf_stats.items():
            if stats.get('count', 0) > 1:
                trends['performance_trends'][metric] = {
                    'improving': stats['max'] < stats['avg'],  # Lower is better for duration
                    'avg_value': stats['avg'],
                    'variability': (stats['max'] - stats['min']) / stats['avg'] if stats['avg'] > 0 else 0
                }
        
        # Analyze operation frequency
        if timeline:
            trends['operation_frequency'] = len(timeline)
            trends['most_recent_operation'] = timeline[-1]['description'] if timeline else None
        
        return trends
    
    def _count_strategies(self, clusters: List[FunctionGroup]) -> Dict[str, int]:
        """Count clustering strategies used."""
        strategy_counts = Counter()
        for cluster in clusters:
            strategy = cluster.metadata.get('clustering_strategy', 'unknown')
            strategy_counts[strategy] += 1
        return dict(strategy_counts)
    
    def _categorize_sizes(self, sizes: List[int]) -> Dict[str, int]:
        """Categorize cluster sizes."""
        categories = {
            'tiny': sum(1 for s in sizes if s < 3),
            'small': sum(1 for s in sizes if 3 <= s < 10),
            'medium': sum(1 for s in sizes if 10 <= s < 20),
            'large': sum(1 for s in sizes if 20 <= s < 50),
            'huge': sum(1 for s in sizes if s >= 50)
        }
        return categories
    
    def _calculate_naming_consistency(self, names: List[str]) -> float:
        """Calculate naming consistency score."""
        if not names:
            return 0.0
        
        # Check for consistent separators
        separator_counts = Counter()
        for name in names:
            if '_' in name:
                separator_counts['underscore'] += 1
            if '-' in name:
                separator_counts['hyphen'] += 1
            if any(c.isupper() for c in name[1:]):
                separator_counts['camelCase'] += 1
        
        # Most common style
        if separator_counts:
            most_common_count = max(separator_counts.values())
            return most_common_count / len(names)
        
        return 1.0  # All names have no separators
    
    def _calculate_cluster_similarity(self, cluster1: FunctionGroup, cluster2: FunctionGroup) -> float:
        """Calculate similarity between two clusters."""
        # Simple similarity based on labels and metadata
        label_sim = self._string_similarity(cluster1.label, cluster2.label)
        
        # Check strategy similarity
        strategy1 = cluster1.metadata.get('clustering_strategy', '')
        strategy2 = cluster2.metadata.get('clustering_strategy', '')
        strategy_sim = 1.0 if strategy1 == strategy2 else 0.0
        
        return (label_sim + strategy_sim) / 2
    
    def _string_similarity(self, s1: str, s2: str) -> float:
        """Calculate simple string similarity."""
        s1_words = set(s1.lower().split())
        s2_words = set(s2.lower().split())
        
        if not s1_words or not s2_words:
            return 0.0
        
        intersection = len(s1_words & s2_words)
        union = len(s1_words | s2_words)
        
        return intersection / union if union > 0 else 0.0
    
    def _calculate_variance(self, values: List[float]) -> float:
        """Calculate variance of values."""
        if not values:
            return 0.0
        
        mean = sum(values) / len(values)
        return sum((x - mean) ** 2 for x in values) / len(values)
    
    def _interpret_quality_score(self, score: float) -> str:
        """Interpret quality score."""
        if score >= 0.8:
            return "Excellent"
        elif score >= 0.6:
            return "Good"
        elif score >= 0.4:
            return "Fair"
        elif score >= 0.2:
            return "Poor"
        else:
            return "Very Poor"