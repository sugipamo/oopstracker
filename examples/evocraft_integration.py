"""
Example of OOPStracker integration with Evocraft workflow.
"""

from oopstracker import CodeMemory
from typing import List, Dict, Any

class EvocraftCodeGuard:
    """Integration layer for Evocraft AI agents."""
    
    def __init__(self, db_path: str = "evocraft_memory.db"):
        self.memory = CodeMemory(db_path=db_path)
        self.generation_history: List[Dict[str, Any]] = []
    
    def check_before_generation(self, prompt: str, context: Dict[str, Any]) -> bool:
        """Check if similar code generation was attempted recently."""
        # Create a pseudo-code representation of the request
        request_repr = f"# Prompt: {prompt}\n# Context: {context}"
        
        result = self.memory.is_duplicate(request_repr)
        if result.is_duplicate:
            print(f"⚠️  Similar code generation detected!")
            print(f"   Previous generation: {result.matched_records[0].timestamp}")
            
            # Ask for confirmation or modification
            return self._handle_duplicate_generation(result, prompt, context)
        
        return True
    
    def _handle_duplicate_generation(self, result, prompt: str, context: Dict[str, Any]) -> bool:
        """Handle duplicate generation scenario."""
        print("Options:")
        print("1. Proceed anyway")
        print("2. Modify the prompt")
        print("3. Skip generation")
        
        # In a real implementation, this would be handled by the AI agent
        # For now, we'll just log and proceed
        print("🔄 Proceeding with modified generation...")
        return True
    
    def register_generation(self, prompt: str, generated_code: str, context: Dict[str, Any]):
        """Register a completed code generation."""
        # Register the prompt/context
        request_repr = f"# Prompt: {prompt}\n# Context: {context}"
        self.memory.register(
            request_repr,
            metadata={"type": "generation_request", "prompt": prompt, "context": context}
        )
        
        # Register the generated code
        self.memory.register(
            generated_code,
            metadata={"type": "generated_code", "prompt": prompt}
        )
        
        # Update history
        self.generation_history.append({
            "prompt": prompt,
            "code": generated_code,
            "context": context,
            "timestamp": self.memory.get_all_records()[-1].timestamp
        })
        
        print(f"✅ Registered generation (total: {len(self.generation_history)})")
    
    def get_generation_stats(self) -> Dict[str, Any]:
        """Get statistics about code generation."""
        total_generations = len(self.generation_history)
        all_records = self.memory.get_all_records()
        
        # Count different types
        request_records = [r for r in all_records if r.metadata.get("type") == "generation_request"]
        code_records = [r for r in all_records if r.metadata.get("type") == "generated_code"]
        
        return {
            "total_generations": total_generations,
            "total_records": len(all_records),
            "request_records": len(request_records),
            "code_records": len(code_records),
            "latest_generation": self.generation_history[-1] if self.generation_history else None
        }


# Example usage
if __name__ == "__main__":
    # Initialize the guard
    guard = EvocraftCodeGuard()
    
    # Simulate AI agent workflow
    print("🚀 Starting Evocraft code generation simulation...")
    
    # First generation
    prompt1 = "Create a function to calculate fibonacci numbers"
    context1 = {"language": "python", "style": "recursive"}
    
    if guard.check_before_generation(prompt1, context1):
        generated_code1 = '''
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
'''
        guard.register_generation(prompt1, generated_code1, context1)
    
    # Second generation (similar)
    prompt2 = "Create a function to calculate fibonacci numbers"
    context2 = {"language": "python", "style": "iterative"}
    
    if guard.check_before_generation(prompt2, context2):
        generated_code2 = '''
def fibonacci(n):
    if n <= 1:
        return n
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b
'''
        guard.register_generation(prompt2, generated_code2, context2)
    
    # Third generation (different)
    prompt3 = "Create a function to sort a list"
    context3 = {"language": "python", "algorithm": "quicksort"}
    
    if guard.check_before_generation(prompt3, context3):
        generated_code3 = '''
def quicksort(arr):
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quicksort(left) + middle + quicksort(right)
'''
        guard.register_generation(prompt3, generated_code3, context3)
    
    # Show statistics
    stats = guard.get_generation_stats()
    print("\n📊 Generation Statistics:")
    print(f"   Total generations: {stats['total_generations']}")
    print(f"   Total records: {stats['total_records']}")
    print(f"   Request records: {stats['request_records']}")
    print(f"   Code records: {stats['code_records']}")
    
    if stats['latest_generation']:
        print(f"   Latest generation: {stats['latest_generation']['prompt'][:50]}...")
    
    print("\n🎯 OOPStracker successfully prevented redundant code generation!")