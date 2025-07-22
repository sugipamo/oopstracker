"""
Demo script for the Function Group Clustering System.

This demonstrates the capabilities of the clustering system including:
- Category-based clustering
- Regex-based cluster splitting
- Clustering insights generation
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.oopstracker.function_group_clustering import FunctionGroupClusteringSystem
from src.oopstracker.clustering_models import ClusteringStrategy


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
        {'name': 'create_user', 'code': 'def create_user(data): return User(**data)', 'file_path': 'users.py'},
        {'name': 'delete_user', 'code': 'def delete_user(id): user_db.delete(id)', 'file_path': 'users.py'},
        {'name': 'load_config', 'code': 'def load_config(): return Config.load()', 'file_path': 'config.py'},
        {'name': 'save_config', 'code': 'def save_config(cfg): cfg.save()', 'file_path': 'config.py'},
        {'name': 'verify_token', 'code': 'def verify_token(token): return token.is_valid()', 'file_path': 'auth.py'},
        {'name': 'generate_token', 'code': 'def generate_token(): return Token.new()', 'file_path': 'auth.py'},
    ]
    
    # Test clustering
    print("\n📊 Creating function clusters...")
    clusters = await clustering_system.get_current_function_clusters(
        mock_functions, 
        ClusteringStrategy.CATEGORY_BASED
    )
    
    for cluster in clusters:
        print(f"\n🏷️  Cluster: {cluster.label}")
        print(f"   ID: {cluster.group_id}")
        print(f"   Functions: {len(cluster.functions)}")
        print(f"   Confidence: {cluster.confidence:.2f}")
        for func in cluster.functions:
            print(f"   - {func['name']} ({func.get('category', 'unknown')})")
    
    # Test splitting
    if clusters:
        # Find a cluster with enough functions to split
        large_clusters = [c for c in clusters if len(c.functions) >= 3]
        
        if large_clusters:
            large_cluster = large_clusters[0]
            print(f"\n✂️  Splitting cluster: {large_cluster.label}")
            print(f"   Current size: {len(large_cluster.functions)} functions")
            
            split_result = await clustering_system.split_cluster_by_regex(
                large_cluster,
                pattern_a=r'get_|fetch_|load_|read_',
                pattern_b=r'set_|update_|save_|create_',
                label_a="Data Retrieval",
                label_b="Data Modification"
            )
            
            print(f"\n   Split Results:")
            print(f"   Group A ({split_result.group_a.label}): {len(split_result.group_a.functions)} functions")
            for func in split_result.group_a.functions:
                print(f"     - {func['name']}")
            
            print(f"\n   Group B ({split_result.group_b.label}): {len(split_result.group_b.functions)} functions")
            for func in split_result.group_b.functions:
                print(f"     - {func['name']}")
            
            if split_result.unmatched:
                print(f"\n   Unmatched: {len(split_result.unmatched)} functions")
                for func in split_result.unmatched:
                    print(f"     - {func['name']}")
            
            print(f"\n   Evaluation scores: A={split_result.evaluation_scores[0]:.2f}, B={split_result.evaluation_scores[1]:.2f}")
    
    # Show insights
    print(f"\n📈 Clustering Insights:")
    insights = clustering_system.get_clustering_insights()
    summary = insights['clustering_summary']
    print(f"   Total clusters: {summary['total_clusters']}")
    print(f"   Total functions: {summary['total_functions']}")
    print(f"   Average cluster size: {summary['average_cluster_size']:.1f}")
    
    if insights['split_history']:
        print(f"\n   Split History:")
        for split in insights['split_history']:
            print(f"   - Split cluster '{split['original_cluster_id']}' into:")
            print(f"     • Group A: {split['group_a_size']} functions (score: {split['evaluation_scores'][0]:.2f})")
            print(f"     • Group B: {split['group_b_size']} functions (score: {split['evaluation_scores'][1]:.2f})")


if __name__ == "__main__":
    asyncio.run(demo_function_clustering())