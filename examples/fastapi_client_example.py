"""
Example client for the FastAPI similarity search server.
"""

import asyncio
import aiohttp
import json
import time
from typing import List, Dict, Any


class OOPSTrackerClient:
    """Client for OOPStracker FastAPI server."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def insert_code(self, code: str, function_name: str = None, 
                         file_path: str = None, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Insert code into the server."""
        data = {
            "text": code,
            "function_name": function_name,
            "file_path": file_path,
            "metadata": metadata or {}
        }
        
        async with self.session.post(f"{self.base_url}/insert", json=data) as response:
            return await response.json()
    
    async def search_similar(self, code: str, threshold: int = 5) -> Dict[str, Any]:
        """Search for similar code."""
        params = {"q": code, "threshold": threshold}
        
        async with self.session.get(f"{self.base_url}/search", params=params) as response:
            return await response.json()
    
    async def list_all_code(self, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
        """List all stored code."""
        params = {"limit": limit, "offset": offset}
        
        async with self.session.get(f"{self.base_url}/list", params=params) as response:
            return await response.json()
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get server statistics."""
        async with self.session.get(f"{self.base_url}/stats") as response:
            return await response.json()
    
    async def health_check(self) -> Dict[str, Any]:
        """Check server health."""
        async with self.session.get(f"{self.base_url}/health") as response:
            return await response.json()


async def demo_basic_usage():
    """Demonstrate basic API usage."""
    print("🚀 Starting FastAPI Client Demo")
    print("=" * 50)
    
    async with OOPSTrackerClient() as client:
        # Health check
        print("1. Health check...")
        try:
            health = await client.health_check()
            print(f"   Status: {health['status']}")
        except Exception as e:
            print(f"   Error: {e}")
            return
        
        # Insert some code samples
        print("\n2. Inserting code samples...")
        
        code_samples = [
            {
                "code": '''
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
''',
                "function_name": "fibonacci_recursive",
                "file_path": "fibonacci.py"
            },
            {
                "code": '''
def fibonacci(n):
    if n <= 1:
        return n
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b
''',
                "function_name": "fibonacci_iterative",
                "file_path": "fibonacci_iter.py"
            },
            {
                "code": '''
def quicksort(arr):
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quicksort(left) + middle + quicksort(right)
''',
                "function_name": "quicksort",
                "file_path": "sorting.py"
            }
        ]
        
        insert_results = []
        for i, sample in enumerate(code_samples):
            try:
                result = await client.insert_code(
                    sample["code"],
                    sample["function_name"],
                    sample["file_path"]
                )
                insert_results.append(result)
                print(f"   Inserted {sample['function_name']}: ID={result['id']}, SimHash={result['simhash']}")
            except Exception as e:
                print(f"   Error inserting {sample['function_name']}: {e}")
        
        # Search for similar code
        print("\n3. Searching for similar code...")
        
        search_queries = [
            {
                "name": "Similar to recursive fibonacci",
                "code": '''
def fib(n):
    # This is very similar to the recursive version
    if n <= 1:
        return n
    return fib(n-1) + fib(n-2)
'''
            },
            {
                "name": "Different algorithm",
                "code": '''
def bubble_sort(arr):
    n = len(arr)
    for i in range(n):
        for j in range(0, n-i-1):
            if arr[j] > arr[j+1]:
                arr[j], arr[j+1] = arr[j+1], arr[j]
    return arr
'''
            }
        ]
        
        for query in search_queries:
            try:
                start_time = time.time()
                result = await client.search_similar(query["code"], threshold=10)
                end_time = time.time()
                
                search_time = (end_time - start_time) * 1000
                
                print(f"   Query: {query['name']}")
                print(f"   Search time: {search_time:.2f} ms (Server: {result['search_time_ms']:.2f} ms)")
                print(f"   Query SimHash: {result['query_simhash']}")
                print(f"   Found {len(result['results'])} similar results:")
                
                for res in result['results']:
                    print(f"     - {res['function_name']}: similarity={res['similarity_score']:.3f}")
                
            except Exception as e:
                print(f"   Error searching for {query['name']}: {e}")
        
        # List all code
        print("\n4. Listing all stored code...")
        try:
            all_code = await client.list_all_code()
            print(f"   Total records: {all_code['total']}")
            print(f"   Showing {len(all_code['items'])} items:")
            
            for item in all_code['items']:
                print(f"     - ID={item['id']}, Function={item['function_name']}, SimHash={item['simhash']}")
                
        except Exception as e:
            print(f"   Error listing code: {e}")
        
        # Get statistics
        print("\n5. Server statistics...")
        try:
            stats = await client.get_stats()
            print(f"   Total records: {stats['total_records']}")
            print(f"   BK-tree stats: {stats['bk_tree_stats']}")
            print(f"   Performance metrics: {stats['performance_metrics']}")
            
        except Exception as e:
            print(f"   Error getting stats: {e}")


async def performance_test():
    """Test API performance with multiple concurrent requests."""
    print("\n🏃‍♂️ Performance Testing")
    print("=" * 50)
    
    async with OOPSTrackerClient() as client:
        # Test concurrent searches
        print("Testing concurrent similarity searches...")
        
        search_code = '''
def test_function():
    return "Hello, World!"
'''
        
        async def single_search():
            try:
                start_time = time.time()
                result = await client.search_similar(search_code)
                end_time = time.time()
                return (end_time - start_time) * 1000
            except Exception as e:
                print(f"Search error: {e}")
                return None
        
        # Run 10 concurrent searches
        concurrent_searches = 10
        start_time = time.time()
        
        tasks = [single_search() for _ in range(concurrent_searches)]
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        total_time = (end_time - start_time) * 1000
        
        valid_results = [r for r in results if r is not None]
        if valid_results:
            avg_time = sum(valid_results) / len(valid_results)
            print(f"   Concurrent searches: {concurrent_searches}")
            print(f"   Total time: {total_time:.2f} ms")
            print(f"   Average response time: {avg_time:.2f} ms")
            print(f"   Requests per second: {concurrent_searches / (total_time / 1000):.2f}")
        
        # Test bulk insertions
        print("\nTesting bulk code insertions...")
        
        async def single_insert(i):
            code = f'''
def auto_generated_function_{i}():
    x = {i}
    y = x * 2
    return y + {i}
'''
            try:
                start_time = time.time()
                result = await client.insert_code(code, f"auto_func_{i}")
                end_time = time.time()
                return (end_time - start_time) * 1000
            except Exception as e:
                print(f"Insert error: {e}")
                return None
        
        # Run 20 concurrent insertions
        concurrent_inserts = 20
        start_time = time.time()
        
        tasks = [single_insert(i) for i in range(concurrent_inserts)]
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        total_time = (end_time - start_time) * 1000
        
        valid_results = [r for r in results if r is not None]
        if valid_results:
            avg_time = sum(valid_results) / len(valid_results)
            print(f"   Concurrent inserts: {concurrent_inserts}")
            print(f"   Total time: {total_time:.2f} ms")
            print(f"   Average response time: {avg_time:.2f} ms")
            print(f"   Inserts per second: {concurrent_inserts / (total_time / 1000):.2f}")


async def main():
    """Run all client examples."""
    try:
        await demo_basic_usage()
        await performance_test()
        
        print("\n" + "=" * 50)
        print("✅ FastAPI Client Demo completed successfully!")
        print("\n💡 Key Observations:")
        print("- FastAPI provides high-performance REST API interface")
        print("- SimHash similarity search maintains sub-second response times")
        print("- Concurrent requests are handled efficiently")
        print("- Suitable for real-time AI agent integration")
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        raise


if __name__ == "__main__":
    print("🌐 OOPStracker FastAPI Client Example")
    print("Make sure to start the server first: uv run python -m oopstracker.api_server")
    print()
    
    asyncio.run(main())