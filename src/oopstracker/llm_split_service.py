"""
LLM Split Service - Handles LLM-based group splitting operations.
Extracted from SmartGroupSplitter to separate LLM concerns.
"""

import re
import random
import asyncio
import logging
import json
import os
from typing import List, Dict, Tuple, Optional
from datetime import datetime
from dataclasses import dataclass

from .function_group_clustering import FunctionGroup
from .split_rule_repository import SplitRule



class LLMSplitService:
    """Service for LLM-based group splitting operations."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.llm_provider = None
        self.llm_config = None
    
    async def _ensure_llm_provider(self):
        """Ensure LLM provider is initialized."""
        if not self.llm_provider:
            # Import llm_providers
            import sys
            sys.path.insert(0, '/home/coding/code-smith/evocraft/packages/llm-providers/src')
            from llm_providers import create_provider, LLMConfig
            
            # Create config using environment variables
            llm_model = os.getenv("OOPSTRACKER_LLM_MODEL")
            if not llm_model:
                raise RuntimeError("OOPSTRACKER_LLM_MODEL environment variable is required. LLM is mandatory for oopstracker.")
            
            self.llm_config = LLMConfig(
                provider="openai",
                model=llm_model,
                temperature=0.3,
                max_tokens=1000
            )
            
            self.llm_provider = await create_provider(self.llm_config)
    
    async def generate_split_pattern(self, sample_functions: List[Dict]) -> Tuple[str, str, str, str]:
        """Generate a regex pattern to split functions using LLM.
        
        Returns:
            Tuple of (pattern, reasoning, group_a_name, group_b_name)
        """
        await self._ensure_llm_provider()
        
        # Prepare prompt
        prompt = self._create_split_prompt(sample_functions)
        
        try:
            # Call LLM
            async with self.llm_provider as provider:
                response = await provider.generate(prompt)
            
            # Parse response - LLMResponse has content attribute
            result = self._parse_llm_response(response.content)
            
            pattern = result.get('pattern', '')
            reasoning = result.get('reasoning', '関数を2つのグループに分割')
            group_a_name = result.get('group_a_name', 'Group A')
            group_b_name = result.get('group_b_name', 'Group B')
            
            self.logger.info(f"LLM generated pattern: {pattern}")
            self.logger.info(f"LLM reasoning: {reasoning}")
            self.logger.info(f"Group A name: {group_a_name}")
            self.logger.info(f"Group B name: {group_b_name}")
            
            return pattern, reasoning, group_a_name, group_b_name
            
        except asyncio.TimeoutError:
            error_msg = "LLM request timed out"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)
        except Exception as e:
            if isinstance(e, RuntimeError):
                raise
            error_msg = f"Unexpected error generating regex with LLM: {e}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    def validate_split_pattern(self, group: FunctionGroup, pattern: str) -> Tuple[bool, List[Dict], List[Dict]]:
        """Validate if a regex pattern creates a valid split.
        
        Returns:
            Tuple of (is_valid, matched_functions, unmatched_functions)
        """
        try:
            matched = []
            unmatched = []
            
            for func in group.functions:
                code = func.get('code', '')
                if re.search(pattern, code, re.MULTILINE | re.DOTALL):
                    matched.append(func)
                else:
                    unmatched.append(func)
            
            # Valid if both groups have functions
            is_valid = len(matched) > 0 and len(unmatched) > 0
            return is_valid, matched, unmatched
            
        except Exception as e:
            self.logger.error(f"Regex validation failed: {e}")
            return False, [], []
    
    async def generate_split_for_group(self, group: FunctionGroup, max_attempts: int = 3) -> Optional[Dict]:
        """Generate a split for a single group using LLM.
        
        Returns:
            Dict with split information or None if failed
        """
        for attempt in range(max_attempts):
            # Sample functions (5 or all if less)
            sample_size = min(5, len(group.functions))
            sample_functions = random.sample(group.functions, sample_size)
            
            try:
                pattern, reasoning, group_a_name, group_b_name = await self.generate_split_pattern(sample_functions)
                is_valid, matched, unmatched = self.validate_split_pattern(group, pattern)
                
                if is_valid:
                    return {
                        'pattern': pattern,
                        'reasoning': reasoning,
                        'group_a_name': group_a_name,
                        'group_b_name': group_b_name,
                        'matched_functions': matched,
                        'unmatched_functions': unmatched,
                        'rule': SplitRule(
                            pattern=pattern,
                            reasoning=reasoning,
                            created_at=datetime.now(),
                            success_count=0,
                            failure_count=0,
                            id=None
                        )
                    }
                else:
                    self.logger.warning(f"Generated pattern '{pattern}' did not create valid split")
                
            except RuntimeError as e:
                self.logger.error(f"Attempt {attempt + 1} failed with error: {e}")
                if attempt == max_attempts - 1:
                    raise RuntimeError(f"Cannot split group {group.group_id}: {e}")
            except Exception as e:
                self.logger.error(f"Unexpected error in attempt {attempt + 1}: {e}")
                if attempt == max_attempts - 1:
                    raise RuntimeError(f"Unexpected error splitting group {group.group_id}: {e}")
        
        return None
    
    def _create_split_prompt(self, sample_functions: List[Dict]) -> str:
        """Create prompt for LLM to generate split pattern."""
        function_list = []
        for i, func in enumerate(sample_functions):
            code = func.get('code', '')
            name = func.get('name', f'function_{i}')
            function_list.append(f"Function {i+1} ({name}):\n```python\n{code}\n```")
        
        functions_text = "\n\n".join(function_list)
        
        prompt = f"""Analyze the following {len(sample_functions)} Python functions and generate a regex pattern to split them into two meaningful groups.

{functions_text}

Return JSON format:
{{
  "pattern": "regex pattern to match some functions",
  "reasoning": "reason for this split",
  "group_a_name": "name for matched functions",
  "group_b_name": "name for non-matched functions"
}}"""
        
        return prompt
    
    def _parse_llm_response(self, response: str) -> Dict:
        """Parse LLM response to extract pattern information."""
        # Direct JSON parsing without fallback
        json_match = re.search(r'\{[\s\S]*\}', response)
        json_str = json_match.group() if json_match else response
        result = json.loads(json_str)
        return result
    
    def generate_split_rules(self, functions: List[Dict], max_rules: int = 3) -> List[SplitRule]:
        """Generate multiple split rules for comprehensive function group analysis.
        
        Args:
            functions: List of function dictionaries with 'name' and 'code' keys
            max_rules: Maximum number of rules to generate
            
        Returns:
            List of SplitRule objects
        """
        rules = []
        attempts = 0
        max_attempts = max_rules * 2  # Allow some failures
        
        while len(rules) < max_rules and attempts < max_attempts:
            try:
                # Generate single pattern using existing async method
                # Run in a separate thread to avoid event loop conflicts
                import concurrent.futures
                import threading
                
                def run_async_in_thread():
                    return asyncio.run(self.generate_split_pattern(functions))
                
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(run_async_in_thread)
                    pattern, reasoning, group_a, group_b = future.result(timeout=30)
                
                # Create SplitRule object
                rule = SplitRule(
                    pattern=pattern,
                    reasoning=f"Rule {len(rules) + 1}: {reasoning}",
                    created_at=datetime.now(),
                    success_count=0,
                    failure_count=0,
                    id=None
                )
                
                # Avoid duplicate patterns
                if not any(existing.pattern == pattern for existing in rules):
                    rules.append(rule)
                    
            except Exception as e:
                self.logger.warning(f"Failed to generate rule {len(rules) + 1}: {e}")
                
            attempts += 1
        
        self.logger.info(f"Generated {len(rules)} split rules")
        return rules