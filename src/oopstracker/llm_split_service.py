"""
LLM Split Service - Handles LLM-based group splitting operations.
Extracted from SmartGroupSplitter to separate LLM concerns.
"""

import re
import random
import asyncio
import logging
from typing import List, Dict, Tuple, Optional
from datetime import datetime

from .function_group_clustering import FunctionGroup
from .ai_analysis_coordinator import get_ai_coordinator
from .llm_prompt_handler import LLMPromptHandler
from .split_rule_repository import SplitRule


class LLMSplitService:
    """Service for LLM-based group splitting operations."""
    
    def __init__(self, enable_ai: bool = True):
        self.logger = logging.getLogger(__name__)
        self.ai_coordinator = get_ai_coordinator() if enable_ai else None
        self.prompt_handler = LLMPromptHandler()
    
    async def generate_split_pattern(self, sample_functions: List[Dict]) -> Tuple[str, str, str, str]:
        """Generate a regex pattern to split functions using LLM.
        
        Returns:
            Tuple of (pattern, reasoning, group_a_name, group_b_name)
        """
        if not self.ai_coordinator:
            error_msg = "AI coordinator not available for LLM-based splitting"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        try:
            response = await self.ai_coordinator.generate_classification_pattern(sample_functions)
            
            if not response or not response.success:
                error_msg = f"LLM response unsuccessful: {response.reasoning if response else 'No response'}"
                self.logger.error(error_msg)
                raise RuntimeError(error_msg)
            
            # Extract pattern information from response
            result = response.result
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
                            created_at=datetime.now()
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