"""
Group Split Coordinator - Coordinates the group splitting process.
Extracted from SmartGroupSplitter to separate orchestration logic.
"""

import logging
from typing import List, Dict, Optional
from datetime import datetime

from .function_group_clustering import FunctionGroup
from .split_rule_repository import SplitRule


class GroupSplitCoordinator:
    """Coordinates the process of splitting groups."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def create_split_groups(
        self, 
        group: FunctionGroup, 
        matched_functions: List[Dict],
        unmatched_functions: List[Dict],
        pattern: str,
        reasoning: str,
        group_a_name: str,
        group_b_name: str,
        split_count: int,
        confidence_factor: float = 0.9
    ) -> tuple[FunctionGroup, FunctionGroup]:
        """Create two subgroups from a split operation."""
        group_a = FunctionGroup(
            group_id=f"{group.group_id}_a",
            functions=matched_functions,
            label=group_a_name,
            confidence=group.confidence * confidence_factor,
            metadata={
                'split_rule': pattern, 
                'split_reason': reasoning,
                'split_count': split_count + 1,
                'parent_group': group.group_id
            }
        )
        
        group_b = FunctionGroup(
            group_id=f"{group.group_id}_b",
            functions=unmatched_functions,
            label=group_b_name,
            confidence=group.confidence * confidence_factor,
            metadata={
                'split_rule': pattern, 
                'split_reason': reasoning,
                'split_count': split_count + 1,
                'parent_group': group.group_id
            }
        )
        
        return group_a, group_b
    
    def create_rule_based_groups(
        self,
        group: FunctionGroup,
        matched_functions: List[Dict],
        unmatched_functions: List[Dict],
        rule: SplitRule,
        split_count: int
    ) -> tuple[FunctionGroup, FunctionGroup]:
        """Create subgroups based on an existing rule."""
        return self.create_split_groups(
            group=group,
            matched_functions=matched_functions,
            unmatched_functions=unmatched_functions,
            pattern=rule.pattern,
            reasoning=rule.reasoning,
            group_a_name=f"{group.label} (Pattern Match)",
            group_b_name=f"{group.label} (No Match)",
            split_count=split_count,
            confidence_factor=0.9
        )
    
    def create_llm_based_groups(
        self,
        group: FunctionGroup,
        split_info: Dict,
        split_count: int
    ) -> tuple[FunctionGroup, FunctionGroup]:
        """Create subgroups based on LLM-generated split info."""
        group_a = FunctionGroup(
            group_id=f"{group.group_id}_llm_a",
            functions=split_info['matched_functions'],
            label=split_info['group_a_name'],
            confidence=group.confidence * 0.85,
            metadata={
                'split_rule': split_info['pattern'], 
                'split_reason': split_info['reasoning'],
                'split_count': split_count + 1,
                'parent_group': group.group_id
            }
        )
        
        group_b = FunctionGroup(
            group_id=f"{group.group_id}_llm_b",
            functions=split_info['unmatched_functions'],
            label=split_info['group_b_name'],
            confidence=group.confidence * 0.85,
            metadata={
                'split_rule': split_info['pattern'], 
                'split_reason': split_info['reasoning'],
                'split_count': split_count + 1,
                'parent_group': group.group_id
            }
        )
        
        return group_a, group_b
    
    def should_skip_group(self, group: FunctionGroup, max_depth: int) -> bool:
        """Check if a group should be skipped from splitting."""
        split_count = group.metadata.get('split_count', 0)
        if split_count >= max_depth:
            self.logger.info(f"Group {group.group_id} has been split {split_count} times, skipping")
            return True
        return False