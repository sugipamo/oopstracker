#!/usr/bin/env python3
"""Test network connection timeouts to the LLM server."""

import socket
import time
import asyncio
import aiohttp

def test_dns_lookup():
    """Test DNS lookup time."""
    start = time.time()
    try:
        socket.gethostbyname('192.168.10.180')
        print(f"DNS lookup took {time.time() - start:.3f}s")
    except Exception as e:
        print(f"DNS lookup failed after {time.time() - start:.3f}s: {e}")

def test_tcp_connect():
    """Test TCP connection time."""
    start = time.time()
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5.0)  # 5 second timeout
    
    try:
        result = sock.connect_ex(('192.168.10.180', 8000))
        elapsed = time.time() - start
        if result == 0:
            print(f"TCP connect succeeded in {elapsed:.3f}s")
        else:
            print(f"TCP connect failed (error {result}) after {elapsed:.3f}s")
    except Exception as e:
        print(f"TCP connect exception after {time.time() - start:.3f}s: {e}")
    finally:
        sock.close()

async def test_http_request():
    """Test HTTP request with various timeouts."""
    url = "http://192.168.10.180:8000/v1/chat/completions"
    
    # Test with different timeout values
    for timeout_val in [1, 5, 15]:
        print(f"\nTesting HTTP request with {timeout_val}s timeout...")
        start = time.time()
        
        timeout = aiohttp.ClientTimeout(total=timeout_val)
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    elapsed = time.time() - start
                    print(f"  HTTP request succeeded in {elapsed:.3f}s")
                    print(f"  Status: {response.status}")
        except asyncio.TimeoutError:
            elapsed = time.time() - start
            print(f"  HTTP request timed out after {elapsed:.3f}s")
        except Exception as e:
            elapsed = time.time() - start
            print(f"  HTTP request failed after {elapsed:.3f}s: {type(e).__name__}: {e}")

async def simulate_llm_provider_init():
    """Simulate what might happen in create_provider with retries."""
    url = "http://192.168.10.180:8000/v1/chat/completions"
    retry_count = 3
    retry_delay = 0.5
    timeout_per_try = 5.0
    
    print(f"\nSimulating LLM provider initialization...")
    print(f"  URL: {url}")
    print(f"  Retries: {retry_count}")
    print(f"  Retry delay: {retry_delay}s")
    print(f"  Timeout per try: {timeout_per_try}s")
    
    total_start = time.time()
    
    for attempt in range(retry_count):
        attempt_start = time.time()
        print(f"\n  Attempt {attempt + 1}/{retry_count}...")
        
        timeout = aiohttp.ClientTimeout(total=timeout_per_try)
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, json={"model": "test", "messages": []}) as response:
                    elapsed = time.time() - attempt_start
                    print(f"    Success in {elapsed:.3f}s")
                    print(f"    Total time: {time.time() - total_start:.3f}s")
                    return
        except asyncio.TimeoutError:
            elapsed = time.time() - attempt_start
            print(f"    Timeout after {elapsed:.3f}s")
        except Exception as e:
            elapsed = time.time() - attempt_start
            print(f"    Failed after {elapsed:.3f}s: {type(e).__name__}")
        
        if attempt < retry_count - 1:
            print(f"    Waiting {retry_delay}s before retry...")
            await asyncio.sleep(retry_delay)
    
    total_elapsed = time.time() - total_start
    print(f"\n  All attempts failed. Total time: {total_elapsed:.3f}s")

def main():
    print("=== Testing Network Timeouts to LLM Server ===\n")
    
    print("1. DNS Lookup Test:")
    test_dns_lookup()
    
    print("\n2. TCP Connection Test:")
    test_tcp_connect()
    
    print("\n3. HTTP Request Tests:")
    asyncio.run(test_http_request())
    
    print("\n4. LLM Provider Initialization Simulation:")
    asyncio.run(simulate_llm_provider_init())

if __name__ == "__main__":
    main()