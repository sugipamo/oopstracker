"""
Example usage of the new UnifiedOOPStracker interface.

This demonstrates how to use the refactored, centralized API.
"""

from oopstracker import UnifiedOOPStracker, AnalysisConfig


def main():
    """Demonstrate the unified interface."""
    
    # Create configuration
    config = AnalysisConfig(
        db_path="example.db",
        threshold=8,
        include_tests=False,
        use_gitignore=True
    )
    
    # Initialize the unified interface
    tracker = UnifiedOOPStracker(config)
    
    # Example 1: Analyze the current directory
    print("=== Analyzing current directory ===")
    summary = tracker.analyze_path(".", "*.py")
    
    print(f"Files analyzed: {summary.total_files}")
    print(f"Functions found: {summary.total_functions}")
    print(f"Duplicate groups: {summary.duplicate_groups}")
    print(f"Analysis method: {summary.analysis_method}")
    
    # Example 2: Check if specific code is duplicate
    print("\n=== Checking specific code ===")
    sample_code = """
def hello_world():
    print("Hello, World!")
    return "greeting"
"""
    
    # Register the code first
    tracker.register_code(sample_code, "hello_world", "example.py")
    
    # Check if similar code is duplicate
    similar_code = """
def hello_world():
    print("Hello, World!")
    return "greeting"
"""
    
    result = tracker.check_duplicate(similar_code, "hello_world_copy")
    print(f"Is duplicate: {result.is_duplicate}")
    print(f"Similarity score: {result.similarity_score:.3f}")
    
    # Example 3: Get system summary
    print("\n=== System Summary ===")
    system_summary = tracker.get_summary()
    for key, value in system_summary.items():
        print(f"{key}: {value}")
    
    print("\nUnified interface demonstration complete!")


if __name__ == "__main__":
    main()