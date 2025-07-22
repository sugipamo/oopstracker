"""
Format utilities for OOPStracker output.
"""
from ..models import CodeRecord


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def format_duplicate_pair(detector, record1: CodeRecord, record2: CodeRecord, similarity: float, index: int) -> str:
    """Format a duplicate pair for display."""
    file1 = detector.db_manager.get_relative_path(record1.file_path) if record1.file_path else 'N/A'
    file2 = detector.db_manager.get_relative_path(record2.file_path) if record2.file_path else 'N/A'
    
    return f"""
   {index}. [{record1.metadata.get('type', 'unknown') if record1.metadata else 'unknown'}] {record1.function_name or 'N/A'} ({file1})
      ≈ [{record2.metadata.get('type', 'unknown') if record2.metadata else 'unknown'}] {record2.function_name or 'N/A'} ({file2})
      Similarity: {similarity:.3f}
      Code size: {len(record1.code_content)} / {len(record2.code_content)} chars
      Hashes: {record1.code_hash[:16]}... / {record2.code_hash[:16]}..."""


def format_semantic_duplicate(detector, sem_dup, index: int) -> str:
    """Format a semantic duplicate for display."""
    record1 = sem_dup.code_record_1
    record2 = sem_dup.code_record_2
    
    file1 = detector.db_manager.get_relative_path(record1.file_path) if record1.file_path else 'N/A'
    file2 = detector.db_manager.get_relative_path(record2.file_path) if record2.file_path else 'N/A'
    
    output = f"""
   {index}. Semantic Match (confidence: {sem_dup.semantic_similarity:.3f}):
      [{record1.metadata.get('type', 'unknown') if record1.metadata else 'unknown'}] {record1.function_name or 'N/A'} ({file1})
      ≈ [{record2.metadata.get('type', 'unknown') if record2.metadata else 'unknown'}] {record2.function_name or 'N/A'} ({file2})
      Structural: {sem_dup.structural_similarity:.3f} | Semantic: {sem_dup.semantic_similarity:.3f}"""
    
    if sem_dup.semantic_explanation:
        output += f"\n      Explanation: {sem_dup.semantic_explanation}"
    
    return output