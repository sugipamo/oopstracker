"""
Function Group Clustering System - Evolution from individual classification to group-based analysis.

This module implements a paradigm shift from "two-function similarity" to "function group clustering",
allowing for more sophisticated analysis of code patterns and relationships.
"""

import re
import logging
import asyncio
from typing import List, Dict, Tuple, Any, Optional
from dataclasses import dataclass
from enum import Enum
from collections import defaultdict

from .models import CodeRecord
from .function_taxonomy_expert import FunctionTaxonomyExpert
from .ai_analysis_coordinator import get_ai_coordinator
# Removed circular import - will use lazy import


@dataclass
class FunctionGroup:
    """Represents a group of functionally related functions."""
    group_id: str
    functions: List[Dict[str, Any]]
    label: str
    confidence: float
    split_patterns: Optional[Tuple[str, str]] = None
    metadata: Dict[str, Any] = None


@dataclass
class ClusterSplitResult:
    """Result of splitting a cluster using regex patterns."""
    original_cluster_id: str
    group_a: FunctionGroup
    group_b: FunctionGroup
    unmatched: List[Dict[str, Any]]
    split_patterns: Tuple[str, str]
    evaluation_scores: Tuple[float, float]


class ClusteringStrategy(Enum):
    """Available clustering strategies."""
    SEMANTIC_SIMILARITY = "semantic_similarity"
    CATEGORY_BASED = "category_based"
    REGEX_PATTERN = "regex_pattern"
    HYBRID = "hybrid"


class FunctionGroupClusteringSystem:
    """
    Advanced function clustering system that groups functions by semantic similarity
    and allows manual refinement through regex-based splitting.
    """
    
    def __init__(self, enable_ai: bool = True):
        self.logger = logging.getLogger(__name__)
        
        # Core components
        self.taxonomy_expert = FunctionTaxonomyExpert(enable_ai=enable_ai)
        self.ai_coordinator = get_ai_coordinator() if enable_ai else None
        
        # Clustering state
        self.current_clusters: List[FunctionGroup] = []
        self.cluster_history: List[Dict[str, Any]] = []
        self.split_patterns: Dict[str, Tuple[str, str]] = {}
        
        # Configuration
        self.min_cluster_size = 3
        self.max_cluster_size = 15
        self.similarity_threshold = 0.7
        
        self.logger.info("Function Group Clustering System initialized")
    
    async def load_all_functions_from_repository(self, code_units: List[Any]) -> List[Dict[str, Any]]:
        """Load and prepare function data from code units."""
        functions = []
        
        for unit in code_units:
            if hasattr(unit, 'type') and unit.type == 'function':
                function_data = {
                    'name': unit.name,
                    'code': unit.source_code,
                    'file_path': unit.file_path,
                    'start_line': getattr(unit, 'start_line', 0),
                    'complexity': getattr(unit, 'complexity_score', 0),
                    'hash': getattr(unit, 'code_hash', ''),
                }
                functions.append(function_data)
        
        self.logger.info(f"Loaded {len(functions)} functions from repository")
        return functions
    
    async def get_current_function_clusters(
        self, 
        functions: List[Dict[str, Any]], 
        strategy: ClusteringStrategy = ClusteringStrategy.CATEGORY_BASED
    ) -> List[FunctionGroup]:
        """Group functions into clusters based on semantic similarity or categories."""
        
        if strategy == ClusteringStrategy.CATEGORY_BASED:
            return await self._cluster_by_category(functions)
        elif strategy == ClusteringStrategy.SEMANTIC_SIMILARITY:
            return await self._cluster_by_similarity(functions)
        elif strategy == ClusteringStrategy.HYBRID:
            return await self._cluster_hybrid(functions)
        else:
            raise ValueError(f"Unsupported clustering strategy: {strategy}")
    
    async def hierarchical_cluster_and_classify(
        self,
        functions: List[Dict[str, Any]],
        max_group_size: int = 50,
        max_depth: int = 8
    ) -> List[FunctionGroup]:
        """Hierarchically cluster and classify functions in a single pass.
        
        This method combines splitting and classification to minimize LLM calls.
        Instead of classifying all functions individually, it:
        1. Splits large groups using LLM-generated patterns
        2. Names/classifies groups during the splitting process
        3. Achieves O(log N) LLM calls instead of O(N)
        
        Args:
            functions: List of function dictionaries
            max_group_size: Maximum size before splitting
            max_depth: Maximum recursion depth
            
        Returns:
            List of classified and appropriately sized function groups
        """
        # Create initial group
        initial_group = FunctionGroup(
            group_id="root",
            functions=functions,
            label="All Functions",
            confidence=1.0,
            metadata={
                "clustering_strategy": "hierarchical",
                "total_functions": len(functions)
            }
        )
        
        # Use SmartGroupSplitter for hierarchical splitting (lazy import)
        from .smart_group_splitter import SmartGroupSplitter
        splitter = SmartGroupSplitter(
            enable_ai=self.ai_coordinator is not None
        )
        
        # Perform hierarchical splitting with classification
        result_groups = await splitter.split_large_groups_with_llm(
            [initial_group],
            max_depth=max_depth
        )
        
        # Log statistics
        self.logger.info(f"Hierarchical clustering complete: {len(functions)} functions -> {len(result_groups)} groups")
        avg_size = sum(len(g.functions) for g in result_groups) / len(result_groups) if result_groups else 0
        self.logger.info(f"Average group size: {avg_size:.1f}")
        
        self.current_clusters = result_groups
        return result_groups
    
    async def _cluster_by_category(self, functions: List[Dict[str, Any]]) -> List[FunctionGroup]:
        """Cluster functions by their classification categories."""
        
        # Classify all functions
        function_data = [(func['code'], func['name']) for func in functions]
        classification_results = await self.taxonomy_expert.analyze_function_collection(function_data)
        
        # Group by category
        category_groups = defaultdict(list)
        for i, result in enumerate(classification_results):
            category = result.primary_category
            function_with_category = functions[i].copy()
            function_with_category['category'] = category
            function_with_category['confidence'] = result.confidence
            category_groups[category].append(function_with_category)
        
        # Create FunctionGroup objects
        clusters = []
        for category, group_functions in category_groups.items():
            if len(group_functions) >= self.min_cluster_size:
                cluster = FunctionGroup(
                    group_id=f"category_{category}_{len(clusters)}",
                    functions=group_functions,
                    label=f"{category.replace('_', ' ').title()} Functions",
                    confidence=sum(f['confidence'] for f in group_functions) / len(group_functions),
                    metadata={
                        'clustering_strategy': 'category_based',
                        'category': category,
                        'function_count': len(group_functions)
                    }
                )
                clusters.append(cluster)
        
        self.current_clusters = clusters
        self.logger.info(f"Created {len(clusters)} category-based clusters")
        return clusters
    
    async def _cluster_by_similarity(self, functions: List[Dict[str, Any]]) -> List[FunctionGroup]:
        """Cluster functions by semantic similarity (placeholder for future implementation)."""
        # For now, create simple clusters based on function name patterns
        pattern_groups = defaultdict(list)
        
        for func in functions:
            name = func['name'].lower()
            if name.startswith(('get_', 'fetch_', 'load_')):
                pattern_groups['data_retrieval'].append(func)
            elif name.startswith(('set_', 'update_', 'save_')):
                pattern_groups['data_modification'].append(func)
            elif name.startswith(('validate_', 'check_', 'verify_')):
                pattern_groups['validation'].append(func)
            elif name.startswith(('__init__', 'create_', 'build_')):
                pattern_groups['construction'].append(func)
            else:
                pattern_groups['general'].append(func)
        
        clusters = []
        for pattern, group_functions in pattern_groups.items():
            if len(group_functions) >= self.min_cluster_size:
                cluster = FunctionGroup(
                    group_id=f"similarity_{pattern}_{len(clusters)}",
                    functions=group_functions,
                    label=f"{pattern.replace('_', ' ').title()} Pattern",
                    confidence=0.8,  # Heuristic confidence
                    metadata={
                        'clustering_strategy': 'semantic_similarity',
                        'pattern': pattern,
                        'function_count': len(group_functions)
                    }
                )
                clusters.append(cluster)
        
        self.current_clusters = clusters
        self.logger.info(f"Created {len(clusters)} similarity-based clusters")
        return clusters
    
    async def _cluster_hybrid(self, functions: List[Dict[str, Any]]) -> List[FunctionGroup]:
        """Combine category and similarity-based clustering."""
        category_clusters = await self._cluster_by_category(functions)
        similarity_clusters = await self._cluster_by_similarity(functions)
        
        # Simple merge: prefer category-based, fall back to similarity
        final_clusters = category_clusters
        
        # Add similarity clusters for functions not in category clusters
        categorized_functions = set()
        for cluster in category_clusters:
            for func in cluster.functions:
                categorized_functions.add(func['name'])
        
        for sim_cluster in similarity_clusters:
            uncategorized_functions = [
                f for f in sim_cluster.functions 
                if f['name'] not in categorized_functions
            ]
            if len(uncategorized_functions) >= self.min_cluster_size:
                sim_cluster.functions = uncategorized_functions
                sim_cluster.group_id = f"hybrid_{sim_cluster.group_id}"
                final_clusters.append(sim_cluster)
        
        self.current_clusters = final_clusters
        self.logger.info(f"Created {len(final_clusters)} hybrid clusters")
        return final_clusters
    
    def select_clusters_that_need_manual_split(
        self, 
        clusters: List[FunctionGroup]
    ) -> List[FunctionGroup]:
        """Select clusters that are too large or have high entropy and need manual splitting."""
        
        candidates = []
        for cluster in clusters:
            function_count = len(cluster.functions)
            
            # Size-based selection
            if function_count > self.max_cluster_size:
                candidates.append(cluster)
                continue
            
            # Confidence-based selection (low confidence indicates high entropy)
            if cluster.confidence < 0.6:
                candidates.append(cluster)
                continue
            
            # Complexity variance (if functions have very different complexity)
            complexities = [f.get('complexity', 0) for f in cluster.functions]
            if complexities and len(set(complexities)) > len(complexities) * 0.7:
                candidates.append(cluster)
        
        self.logger.info(f"Selected {len(candidates)} clusters for manual splitting")
        return candidates
    
    async def split_cluster_by_regex(
        self, 
        cluster: FunctionGroup, 
        pattern_a: str, 
        pattern_b: str,
        label_a: str = None,
        label_b: str = None
    ) -> ClusterSplitResult:
        """Split a cluster into two groups using regex patterns."""
        
        group_a_functions = []
        group_b_functions = []
        unmatched_functions = []
        
        # Apply regex patterns
        for func in cluster.functions:
            code = func.get('code', '')
            if re.search(pattern_a, code, re.MULTILINE | re.DOTALL):
                group_a_functions.append(func)
            elif re.search(pattern_b, code, re.MULTILINE | re.DOTALL):
                group_b_functions.append(func)
            else:
                unmatched_functions.append(func)
        
        # Generate labels using LLM if not provided
        if not label_a and group_a_functions:
            label_a = await self._get_function_group_label_from_llm(group_a_functions)
        if not label_b and group_b_functions:
            label_b = await self._get_function_group_label_from_llm(group_b_functions)
        
        # Create new groups
        group_a = FunctionGroup(
            group_id=f"{cluster.group_id}_split_a",
            functions=group_a_functions,
            label=label_a or "Pattern A Group",
            confidence=0.8,
            split_patterns=(pattern_a, pattern_b),
            metadata={
                'parent_cluster': cluster.group_id,
                'split_pattern': pattern_a,
                'split_timestamp': asyncio.get_event_loop().time()
            }
        )
        
        group_b = FunctionGroup(
            group_id=f"{cluster.group_id}_split_b",
            functions=group_b_functions,
            label=label_b or "Pattern B Group",
            confidence=0.8,
            split_patterns=(pattern_a, pattern_b),
            metadata={
                'parent_cluster': cluster.group_id,
                'split_pattern': pattern_b,
                'split_timestamp': asyncio.get_event_loop().time()
            }
        )
        
        # Evaluate labels
        score_a = await self._evaluate_function_group_label_with_llm(group_a_functions, label_a or "Pattern A Group")
        score_b = await self._evaluate_function_group_label_with_llm(group_b_functions, label_b or "Pattern B Group")
        
        result = ClusterSplitResult(
            original_cluster_id=cluster.group_id,
            group_a=group_a,
            group_b=group_b,
            unmatched=unmatched_functions,
            split_patterns=(pattern_a, pattern_b),
            evaluation_scores=(score_a, score_b)
        )
        
        # Record the split
        self._record_split_result_metadata(result)
        
        self.logger.info(f"Split cluster {cluster.group_id}: {len(group_a_functions)} + {len(group_b_functions)} functions ({len(unmatched_functions)} unmatched)")
        return result
    
    async def _get_function_group_label_from_llm(self, function_group: List[Dict[str, Any]]) -> str:
        """Generate a semantic label for a function group using LLM."""
        
        if not self.ai_coordinator:
            # Fallback: generate simple label from function names
            names = [f.get('name', '') for f in function_group]
            common_words = set()
            for name in names:
                words = re.findall(r'[a-zA-Z]+', name.lower())
                common_words.update(words)
            
            if len(common_words) > 0:
                return f"{list(common_words)[0].title()} Related Functions"
            return "Function Group"
        
        # Prepare function summary for LLM
        function_summary = []
        for func in function_group[:5]:  # Limit to first 5 functions
            name = func.get('name', 'unknown')
            code_preview = func.get('code', '')[:100].replace('\n', ' ')
            function_summary.append(f"- {name}: {code_preview}...")
        
        summary_text = "\n".join(function_summary)
        
        prompt = f"""
        Analyze these related functions and provide a concise, descriptive label (2-4 words) that captures their common purpose:

        {summary_text}

        Label (2-4 words):
        """
        
        try:
            response = await self.ai_coordinator.analyze_intent(prompt)
            if response.success:
                label = response.result.get('purpose', 'Function Group')
                # Clean and shorten the label
                label = re.sub(r'[^\w\s]', '', label)
                words = label.split()[:4]  # Max 4 words
                return ' '.join(words).title()
        except Exception as e:
            self.logger.warning(f"LLM label generation failed: {e}")
        
        return "Function Group"
    
    async def _evaluate_function_group_label_with_llm(self, function_group: List[Dict[str, Any]], label: str) -> float:
        """Evaluate the appropriateness of a label for a function group."""
        
        if not self.ai_coordinator:
            # Fallback: simple heuristic evaluation
            names = [f.get('name', '') for f in function_group]
            label_words = set(label.lower().split())
            name_words = set()
            for name in names:
                name_words.update(re.findall(r'[a-zA-Z]+', name.lower()))
            
            overlap = len(label_words & name_words)
            return min(0.9, 0.3 + (overlap * 0.15))
        
        # Prepare evaluation prompt
        function_names = [f.get('name', '') for f in function_group]
        names_text = ", ".join(function_names[:10])
        
        prompt = f"""
        Evaluate how well the label "{label}" describes this group of functions:
        Functions: {names_text}

        Rate the appropriateness on a scale of 0.0 to 1.0:
        - 1.0: Perfect match, label accurately captures the group's purpose
        - 0.7: Good match, mostly appropriate
        - 0.5: Acceptable, somewhat relevant
        - 0.3: Poor match, label doesn't fit well
        - 0.0: Completely inappropriate

        Score (0.0-1.0):
        """
        
        try:
            response = await self.ai_coordinator.analyze_intent(prompt)
            if response.success and response.confidence > 0.5:
                # Extract score from response
                result_text = str(response.result.get('purpose', '0.5'))
                score_match = re.search(r'(\d+\.?\d*)', result_text)
                if score_match:
                    score = float(score_match.group(1))
                    return min(1.0, max(0.0, score))
        except Exception as e:
            self.logger.warning(f"LLM label evaluation failed: {e}")
        
        return 0.5  # Default neutral score
    
    def _record_split_result_metadata(self, split_result: ClusterSplitResult):
        """Record split result metadata for learning and history."""
        
        metadata = {
            'timestamp': asyncio.get_event_loop().time(),
            'original_cluster_id': split_result.original_cluster_id,
            'split_patterns': split_result.split_patterns,
            'group_a_label': split_result.group_a.label,
            'group_b_label': split_result.group_b.label,
            'evaluation_scores': split_result.evaluation_scores,
            'group_a_size': len(split_result.group_a.functions),
            'group_b_size': len(split_result.group_b.functions),
            'unmatched_size': len(split_result.unmatched),
        }
        
        self.cluster_history.append(metadata)
        
        # Store successful patterns for reuse
        if min(split_result.evaluation_scores) > 0.7:
            pattern_key = f"{split_result.group_a.label}_{split_result.group_b.label}"
            self.split_patterns[pattern_key] = split_result.split_patterns
        
        self.logger.debug(f"Recorded split metadata for {split_result.original_cluster_id}")
    
    def get_clustering_insights(self) -> Dict[str, Any]:
        """Get insights about the clustering performance and history."""
        
        total_splits = len(self.cluster_history)
        successful_splits = len([h for h in self.cluster_history if min(h['evaluation_scores']) > 0.7])
        
        if not self.current_clusters:
            return {"message": "No clusters available"}
        
        total_functions = sum(len(cluster.functions) for cluster in self.current_clusters)
        avg_cluster_size = total_functions / len(self.current_clusters)
        
        insights = {
            'clustering_summary': {
                'total_clusters': len(self.current_clusters),
                'total_functions': total_functions,
                'average_cluster_size': avg_cluster_size,
                'split_history': {
                    'total_splits': total_splits,
                    'successful_splits': successful_splits,
                    'success_rate': successful_splits / total_splits if total_splits > 0 else 0.0
                }
            },
            'cluster_details': [
                {
                    'group_id': cluster.group_id,
                    'label': cluster.label,
                    'size': len(cluster.functions),
                    'confidence': cluster.confidence,
                    'strategy': cluster.metadata.get('clustering_strategy', 'unknown')
                }
                for cluster in self.current_clusters
            ],
            'learned_patterns': list(self.split_patterns.keys())
        }
        
        return insights


async def demo_function_clustering():
    """Demo the function group clustering system."""
    print("🔬 Function Group Clustering System Demo")
    print("=" * 50)
    
    # Initialize system
    clustering_system = FunctionGroupClusteringSystem(enable_ai=True)
    
    # Mock function data
    mock_functions = [
        {'name': 'get_user_data', 'code': 'def get_user_data(): return user_db.fetch()', 'file_path': 'users.py'},
        {'name': 'set_user_name', 'code': 'def set_user_name(name): user.name = name', 'file_path': 'users.py'},
        {'name': 'validate_email', 'code': 'def validate_email(email): return "@" in email', 'file_path': 'validation.py'},
        {'name': 'fetch_profile', 'code': 'def fetch_profile(): return profile_db.get()', 'file_path': 'profile.py'},
        {'name': 'update_settings', 'code': 'def update_settings(settings): config.update(settings)', 'file_path': 'config.py'},
        {'name': 'check_password', 'code': 'def check_password(pwd): return len(pwd) > 8', 'file_path': 'validation.py'},
    ]
    
    # Test clustering
    print("📊 Creating function clusters...")
    clusters = await clustering_system.get_current_function_clusters(mock_functions, ClusteringStrategy.CATEGORY_BASED)
    
    for cluster in clusters:
        print(f"\n🏷️  Cluster: {cluster.label}")
        print(f"   Functions: {len(cluster.functions)}")
        print(f"   Confidence: {cluster.confidence:.2f}")
        for func in cluster.functions:
            print(f"   - {func['name']} ({func.get('category', 'unknown')})")
    
    # Test splitting
    if clusters:
        large_cluster = max(clusters, key=lambda c: len(c.functions))
        if len(large_cluster.functions) >= 2:
            print(f"\n✂️  Splitting cluster: {large_cluster.label}")
            
            split_result = await clustering_system.split_cluster_by_regex(
                large_cluster,
                pattern_a=r'get_|fetch_',
                pattern_b=r'set_|update_',
                label_a="Data Retrieval",
                label_b="Data Modification"
            )
            
            print(f"   Group A ({split_result.group_a.label}): {len(split_result.group_a.functions)} functions")
            print(f"   Group B ({split_result.group_b.label}): {len(split_result.group_b.functions)} functions")
            print(f"   Unmatched: {len(split_result.unmatched)} functions")
            print(f"   Evaluation scores: {split_result.evaluation_scores}")
    
    # Show insights
    print(f"\n📈 Clustering Insights:")
    insights = clustering_system.get_clustering_insights()
    summary = insights['clustering_summary']
    print(f"   Total clusters: {summary['total_clusters']}")
    print(f"   Total functions: {summary['total_functions']}")
    print(f"   Average cluster size: {summary['average_cluster_size']:.1f}")


if __name__ == "__main__":
    asyncio.run(demo_function_clustering())