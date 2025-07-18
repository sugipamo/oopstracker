#!/usr/bin/env python3
"""Test LLM availability and connectivity."""

import asyncio
import aiohttp
import sys
import os

async def test_llm_connectivity():
    """Test if LLM endpoint is reachable."""
    
    # Known LLM endpoints
    endpoints = [
        "http://192.168.10.180:8000/v1/chat/completions",
        "http://localhost:8000/v1/chat/completions",
        "http://127.0.0.1:8000/v1/chat/completions",
        "http://localhost:11434/api/chat",  # Ollama default
        "http://127.0.0.1:11434/api/chat",  # Ollama default
    ]
    
    test_payload = {
        "model": "llama2",  # Try common model name
        "messages": [{"role": "user", "content": "test"}],
        "max_tokens": 10
    }
    
    # Also try Ollama format
    ollama_payload = {
        "model": "llama2",
        "messages": [{"role": "user", "content": "test"}],
        "stream": False
    }
    
    print("Testing LLM connectivity...")
    print(f"Current environment: {os.environ.get('LLM_API_URL', 'Not set')}")
    
    for endpoint in endpoints:
        print(f"\n{'='*60}")
        print(f"Testing: {endpoint}")
        
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                # Try OpenAI format first
                async with session.post(endpoint, json=test_payload) as response:
                    print(f"Status: {response.status}")
                    if response.status == 200:
                        data = await response.json()
                        print("✓ SUCCESS - OpenAI format works")
                        print(f"Response keys: {list(data.keys())}")
                        return endpoint
                    elif response.status == 404:
                        print("✗ 404 - Endpoint not found")
                    else:
                        text = await response.text()
                        print(f"✗ Error: {text[:200]}")
                        
        except aiohttp.ClientError as e:
            print(f"✗ Connection failed: {type(e).__name__}: {e}")
        except Exception as e:
            print(f"✗ Unexpected error: {e}")
            
        # Try Ollama format if endpoint looks like Ollama
        if "11434" in endpoint:
            try:
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                    async with session.post(endpoint, json=ollama_payload) as response:
                        print(f"Ollama format - Status: {response.status}")
                        if response.status == 200:
                            print("✓ SUCCESS - Ollama format works")
                            return endpoint
            except:
                pass
    
    print("\n❌ No working LLM endpoint found")
    return None

async def test_llm_providers_import():
    """Test if llm_providers can be imported."""
    print("\n" + "="*60)
    print("Testing llm_providers import...")
    
    # Check various paths
    paths_to_check = [
        "/home/coding/code-smith/util/llm-providers/src",
        "./llm_providers",
        "../llm_providers",
        "../../util/llm-providers/src",
    ]
    
    for path in paths_to_check:
        if os.path.exists(path):
            print(f"✓ Found path: {path}")
            sys.path.insert(0, path)
            try:
                from llm_providers import create_provider, LLMConfig
                print("✓ Successfully imported llm_providers")
                return True
            except ImportError as e:
                print(f"✗ Import failed: {e}")
                sys.path.pop(0)
    
    print("✗ llm_providers module not found")
    return False

async def test_semantic_analyzer():
    """Test if semantic analyzer can be initialized."""
    print("\n" + "="*60)
    print("Testing semantic analyzer...")
    
    try:
        # Add venv path
        venv_path = "/home/coding/code-smith/code-generation/intent/ast-analysis/oopstracker/.venv/lib/python3.12/site-packages"
        if venv_path not in sys.path:
            sys.path.insert(0, venv_path)
        
        from intent_unified.core.semantic_analyzer import SemanticDuplicateAnalyzer
        print("✓ Successfully imported SemanticDuplicateAnalyzer")
        
        # Check if it has the modified code
        analyzer = SemanticDuplicateAnalyzer()
        if hasattr(analyzer, 'initialize'):
            print("✓ Analyzer has initialize method")
            
            # Check source
            import inspect
            source = inspect.getsource(analyzer.initialize)
            if "192.168.10.180:8000" in source:
                print("✓ Analyzer has hardcoded LLM endpoint")
            else:
                print("✗ Analyzer missing hardcoded endpoint")
                
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

async def main():
    """Run all tests."""
    print("OOPStracker LLM Availability Test")
    print("="*60)
    
    # Test 1: LLM connectivity
    working_endpoint = await test_llm_connectivity()
    
    # Test 2: llm_providers import
    providers_available = await test_llm_providers_import()
    
    # Test 3: semantic analyzer
    analyzer_available = await test_semantic_analyzer()
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY:")
    print(f"LLM Endpoint: {'✓ Available' if working_endpoint else '✗ Not available'}")
    print(f"LLM Providers: {'✓ Available' if providers_available else '✗ Not available'}")
    print(f"Semantic Analyzer: {'✓ Available' if analyzer_available else '✗ Not available'}")
    
    if not working_endpoint:
        print("\nPossible solutions:")
        print("1. Install and run Ollama: curl -fsSL https://ollama.com/install.sh | sh")
        print("2. Start Ollama: ollama serve")
        print("3. Pull a model: ollama pull llama2")
        print("4. Or ensure your LLM service is running at one of the tested endpoints")

if __name__ == "__main__":
    asyncio.run(main())