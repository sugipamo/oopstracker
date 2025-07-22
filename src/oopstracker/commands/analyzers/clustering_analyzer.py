"""
Function clustering analyzer.
"""

from typing import List, Dict, Any
from .base import BaseAnalyzer, AnalysisResult
from ...function_group_clustering import FunctionGroupClusteringSystem, ClusteringStrategy


class ClusteringAnalyzer(BaseAnalyzer):
    """Analyzer for function group clustering."""
    
    async def analyze(self, **kwargs) -> AnalysisResult:
        """Perform clustering analysis."""
        clustering_system = FunctionGroupClusteringSystem(enable_ai=True)
        
        # Load functions from detector
        all_functions = await clustering_system.load_all_functions_from_repository(
            list(self.detector.code_units.values())
        )
        
        if not all_functions:
            return AnalysisResult(
                success=True,
                data={},
                summary="No functions found for clustering analysis"
            )
        
        # Convert strategy string to enum
        strategy_map = {
            'category_based': ClusteringStrategy.CATEGORY_BASED,
            'semantic_similarity': ClusteringStrategy.SEMANTIC_SIMILARITY,
            'hybrid': ClusteringStrategy.HYBRID
        }
        strategy = strategy_map.get(
            getattr(self.args, 'clustering_strategy', 'category_based'), 
            ClusteringStrategy.CATEGORY_BASED
        )
        
        # Create clusters
        clusters = await clustering_system.get_current_function_clusters(
            all_functions, strategy
        )
        
        # Identify clusters that need splitting
        split_candidates = clustering_system.select_clusters_that_need_manual_split(clusters)
        
        # Get clustering insights
        insights = clustering_system.get_clustering_insights()
        
        return AnalysisResult(
            success=True,
            data={
                'function_count': len(all_functions),
                'clusters': clusters,
                'split_candidates': split_candidates,
                'insights': insights,
                'strategy': getattr(self.args, 'clustering_strategy', 'category_based'),
                'max_cluster_size': clustering_system.max_cluster_size
            },
            summary=f"Created {len(clusters)} function groups from {len(all_functions)} functions"
        )
    
    def display_results(self, result: AnalysisResult) -> None:
        """Display clustering results."""
        data = result.data
        
        print(f"\n🔬 Function Group Clustering Analysis")
        
        if not data.get('clusters'):
            print("   No functions found for clustering analysis")
            return
        
        print(f"   Clustering {data['function_count']} functions using {data['strategy']} strategy...")
        
        # Display cluster summary
        clusters = data['clusters']
        print(f"\n   📊 Clustering Results:")
        print(f"      Created {len(clusters)} function groups")
        
        for i, cluster in enumerate(clusters, 1):
            if hasattr(self.args, 'verbose') and self.args.verbose:
                print(f"\n   🏷️  Group {i}: {cluster.label}")
                print(f"      Functions: {len(cluster.functions)} (confidence: {cluster.confidence:.2f})")
                for func in cluster.functions[:3]:  # Show first 3 functions
                    print(f"      - {func['name']} ({func.get('file_path', 'unknown')})")
                if len(cluster.functions) > 3:
                    print(f"      - ... and {len(cluster.functions) - 3} more")
            else:
                print(f"      Group {i}: {cluster.label} ({len(cluster.functions)} functions, confidence: {cluster.confidence:.2f})")
        
        # Display split candidates
        split_candidates = data.get('split_candidates', [])
        if split_candidates:
            print(f"\n   ✂️  Split Candidates: {len(split_candidates)} large/complex groups could benefit from manual splitting")
            for candidate in split_candidates[:3]:  # Show first 3 candidates
                reason = "large size" if len(candidate.functions) > data['max_cluster_size'] else "low confidence"
                print(f"      - {candidate.label}: {len(candidate.functions)} functions ({reason})")
        
        # Show clustering insights
        insights = data.get('insights', {})
        summary = insights.get('clustering_summary', {})
        
        print(f"\n   📈 Insights:")
        if 'average_cluster_size' in summary:
            print(f"      Average group size: {summary['average_cluster_size']:.1f}")
        
        split_history = summary.get('split_history', {})
        if split_history.get('total_splits', 0) > 0:
            print(f"      Split success rate: {split_history['success_rate']:.1%}")
        
        if hasattr(self.args, 'verbose') and self.args.verbose:
            print(f"      💡 Use clustering to understand code organization patterns")
            print(f"      💡 Large groups may indicate opportunities for refactoring")