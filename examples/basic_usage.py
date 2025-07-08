"""
Basic usage example for OOPStracker.
"""

from oopstracker import CodeMemory

# Initialize code memory
memory = CodeMemory(db_path="example.db")

# Sample code snippets
code1 = '''
def hello():
    print("Hello, world!")
'''

code2 = '''
def hello():
    print("Hello, world!")
    # Added comment
'''

code3 = '''
def greet(name):
    print(f"Hello, {name}!")
'''

# Register first code snippet
print("Registering first code snippet...")
record1 = memory.register(code1, function_name="hello")
print(f"✅ Registered with hash: {record1.code_hash}")

# Check if second code is duplicate (should be, after normalization)
print("\nChecking second code snippet...")
result = memory.is_duplicate(code2)
if result.is_duplicate:
    print("⚠️  Duplicate detected!")
    for record in result.matched_records:
        print(f"   Similar to: {record.function_name} (score: {result.similarity_score})")
else:
    print("✅ No duplicates found")

# Check third code (should not be duplicate)
print("\nChecking third code snippet...")
result = memory.is_duplicate(code3)
if result.is_duplicate:
    print("⚠️  Duplicate detected!")
else:
    print("✅ No duplicates found")
    # Register it
    record3 = memory.register(code3, function_name="greet")
    print(f"✅ Registered with hash: {record3.code_hash}")

# List all registered code
print("\nAll registered code:")
all_records = memory.get_all_records()
for record in all_records:
    print(f"- {record.function_name}: {record.code_hash[:16]}...")

print(f"\nTotal registered: {len(all_records)} code snippets")