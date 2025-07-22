#!/usr/bin/env python3
"""
Fix LLM prompting to work with natural language responses.

This addresses the core issue: forcing structured output from 
a conversational LLM instead of working with its natural responses.
"""

import asyncio
import sys
import re
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from oopstracker.ai_analysis_coordinator import get_ai_coordinator


async def test_natural_language_approach():
    """Test working WITH the LLM's natural language instead of fighting it."""
    print("🔧 Testing Natural Language LLM Approach")
    print("=" * 50)
    
    coordinator = get_ai_coordinator(use_mock=False)
    
    # Sample functions 
    functions = [
        "create_user_profile", "validate_email_format", "update_user_settings",
        "check_permission_access", "generate_api_token"
    ]
    
    # Natural language prompt that works WITH the LLM
    natural_prompt = f"""I have these Python functions:
{', '.join(functions)}

I need to split them into 2 groups for refactoring. Can you suggest a way to categorize them? 
For example, you might group them by:
- Create/update operations vs validation/checking operations
- User-related vs system-related functions
- Or any other logical grouping you see

Please explain your reasoning and give me a simple rule I can use to split them."""
    
    print(f"📤 Sending natural language prompt...")
    start_time = time.time()
    
    try:
        response = await coordinator.analyze_intent(natural_prompt)
        elapsed = time.time() - start_time
        
        print(f"✅ Response received in {elapsed:.1f}s")
        
        if response.success:
            result = response.result.get('purpose', '') if isinstance(response.result, dict) else str(response.result)
            print(f"🤖 LLM Response:")
            print(f"   {result[:300]}...")
            
            # Extract actionable patterns from natural language
            patterns = extract_patterns_from_natural_response(result, functions)
            
            if patterns:
                print(f"\n✅ Extracted actionable patterns:")
                for pattern, reasoning in patterns:
                    print(f"   Pattern: {pattern}")
                    print(f"   Reasoning: {reasoning}")
                    
                    # Test the pattern
                    matches = test_pattern_against_functions(pattern, functions)
                    print(f"   Matches: {matches}/{len(functions)} functions")
                    print()
                
                return True
            else:
                print(f"❌ Could not extract actionable patterns from response")
                return False
        else:
            print(f"❌ LLM response failed: {response.reasoning}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def extract_patterns_from_natural_response(response_text: str, functions: list) -> list:
    """
    Extract actionable regex patterns from LLM's natural language response.
    
    This works WITH the LLM instead of fighting it.
    """
    patterns = []
    
    # Look for grouping suggestions in natural language
    response_lower = response_text.lower()
    
    # Pattern 1: Create/Update vs others
    if any(word in response_lower for word in ['create', 'update', 'modify']):
        pattern = r'def\s+(create|update|modify|add|set)_'
        reasoning = "Create/update/modify operations vs other operations"
        patterns.append((pattern, reasoning))
    
    # Pattern 2: Validation/Check vs others  
    if any(word in response_lower for word in ['validate', 'check', 'verify']):
        pattern = r'def\s+(validate|check|verify|test|is_|has_)_'
        reasoning = "Validation/checking functions vs operational functions"
        patterns.append((pattern, reasoning))
    
    # Pattern 3: User-related vs system
    if any(word in response_lower for word in ['user', 'account', 'profile']):
        pattern = r'def\s+\w*user\w*|def\s+\w*profile\w*|def\s+\w*account\w*'
        reasoning = "User-related functions vs system functions"
        patterns.append((pattern, reasoning))
    
    # Pattern 4: GET vs POST-like operations
    if any(word in response_lower for word in ['get', 'retrieve', 'fetch']):
        pattern = r'def\s+(get|fetch|retrieve|find|load)_'
        reasoning = "Read operations vs write operations"
        patterns.append((pattern, reasoning))
    
    # Fallback: Extract actual function names mentioned
    mentioned_functions = []
    for func in functions:
        if func.lower() in response_lower:
            mentioned_functions.append(func)
    
    if len(mentioned_functions) >= 2:
        func_group = '|'.join(mentioned_functions[:len(mentioned_functions)//2])
        pattern = f'def\\s+({func_group})'
        reasoning = f"LLM suggested grouping: {', '.join(mentioned_functions[:len(mentioned_functions)//2])}"
        patterns.append((pattern, reasoning))
    
    return patterns


def test_pattern_against_functions(pattern: str, functions: list) -> int:
    """Test how many functions match a given pattern."""
    matches = 0
    try:
        for func in functions:
            if re.search(pattern, f"def {func}()", re.IGNORECASE):
                matches += 1
    except re.error:
        pass
    return matches


async def test_conversational_refinement():
    """Test iterative refinement through conversation with LLM."""
    print(f"\n💬 Testing Conversational Refinement")
    print("=" * 50)
    
    coordinator = get_ai_coordinator(use_mock=False)
    
    functions = [
        "create_user_profile", "get_user_by_id", "validate_email_format",
        "update_user_settings", "check_permission_access", "generate_api_token",
        "delete_user_account", "authenticate_user", "log_user_activity"
    ]
    
    # First question
    first_prompt = f"""I have these 9 Python functions: {', '.join(functions)}

Looking at these function names, what do you notice about them? 
What are the main categories or types of operations?"""
    
    print(f"📤 First question...")
    response1 = await coordinator.analyze_intent(first_prompt)
    
    if response1.success:
        result1 = response1.result.get('purpose', '') if isinstance(response1.result, dict) else str(response1.result)
        print(f"🤖 LLM identified categories")
        
        # Follow-up question
        followup_prompt = f"""Based on your analysis, if I wanted to split these functions into exactly 2 groups for refactoring, which functions would you put together?

Functions: {', '.join(functions)}

Please give me 2 clear groups."""
        
        print(f"📤 Follow-up question...")
        response2 = await coordinator.analyze_intent(followup_prompt)
        
        if response2.success:
            result2 = response2.result.get('purpose', '') if isinstance(response2.result, dict) else str(response2.result)
            print(f"🤖 LLM suggested grouping")
            
            # Try to extract the groups from the response
            groups = extract_groups_from_response(result2, functions)
            
            if groups:
                print(f"\n✅ Extracted groups:")
                for i, group in enumerate(groups, 1):
                    print(f"   Group {i}: {group}")
                
                # This is more reliable than regex patterns!
                return True
    
    return False


def extract_groups_from_response(response_text: str, functions: list) -> list:
    """Extract function groups from LLM's natural language response."""
    groups = []
    
    # Look for numbered lists or bullet points
    lines = response_text.split('\n')
    current_group = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Check if any function names are mentioned in this line
        mentioned_in_line = []
        for func in functions:
            if func.lower() in line.lower():
                mentioned_in_line.append(func)
        
        if mentioned_in_line:
            if any(marker in line.lower() for marker in ['group 1', '1.', 'first']):
                if not groups:
                    groups.append([])
                groups[0].extend(mentioned_in_line)
            elif any(marker in line.lower() for marker in ['group 2', '2.', 'second']):
                if len(groups) < 2:
                    groups.append([])
                groups[1].extend(mentioned_in_line)
            else:
                # Add to current group
                if not groups:
                    groups.append([])
                groups[-1].extend(mentioned_in_line)
    
    # Remove duplicates and empty groups
    groups = [list(set(group)) for group in groups if group]
    
    return groups


async def main():
    """Test the natural language approach to LLM interaction."""
    print("🎯 Testing LLM with Natural Language Approach")
    print("Working WITH the LLM instead of forcing structured output\n")
    
    success1 = await test_natural_language_approach()
    success2 = await test_conversational_refinement()
    
    print(f"\n{'='*60}")
    
    if success1 or success2:
        print("🎉 Natural language approach shows promise!")
        print("✅ LLM can provide useful grouping suggestions")
        print("✅ We can extract actionable patterns from natural responses")
        print("✅ This is more aligned with how LLMs actually work")
        print(f"\n💡 Key insight: Work WITH the LLM's conversational nature")
        print(f"   instead of forcing it into rigid output formats.")
    else:
        print("❌ Natural language approach needs more work")
    
    return success1 or success2


if __name__ == "__main__":
    success = asyncio.run(main())
    print(f"\n🎯 Natural language LLM approach: {'✅ Promising' if success else '❌ Needs work'}")