"""
Smart Group Splitter - Intelligent subdivision of large function groups.
Refactored to use extracted components for better separation of concerns.
"""

import re
import random
import asyncio
import logging
from typing import List, Dict, Tuple, Any, Optional
from datetime import datetime

from .function_group_clustering import FunctionGroup, ClusterSplitResult
from .split_strategy_manager import SplitStrategyManager
from .split_rule_repository import SplitRuleRepository, SplitRule
from .llm_split_service import LLMSplitService
from .group_split_coordinator import GroupSplitCoordinator


class SmartGroupSplitter:
    """Intelligent splitter that uses domain knowledge to subdivide large groups."""
    
    def __init__(self, enable_ai: bool = True):
        # Target size for subdivided groups
        self.target_group_size = 12
        self.max_group_size = 20
        
        # LLM-based splitting threshold
        self.llm_group_threshold = 100
        
        # Initialize extracted components
        self.strategy_manager = SplitStrategyManager()
        self.rule_repository = SplitRuleRepository()
        self.llm_service = LLMSplitService(enable_ai=enable_ai)
        self.split_coordinator = GroupSplitCoordinator()
        self.logger = logging.getLogger(__name__)
    
    def should_split(self, group: FunctionGroup) -> bool:
        """Determine if a group needs splitting based on size."""
        return len(group.functions) > self.max_group_size
    
    def recommend_split_strategy(self, group: FunctionGroup):
        """Recommend appropriate split strategy based on group type."""
        return self.strategy_manager.recommend_strategy(group)
    
    def _create_subgroups_from_split_results(self, group: FunctionGroup, split_results: List[Dict]) -> List[FunctionGroup]:
        """Create FunctionGroup objects from split results."""
        subgroups = []
        for i, result in enumerate(split_results):
            subgroup = FunctionGroup(
                group_id=f"{group.group_id}_sub_{i}",
                functions=result['functions'],
                label=result['label'],
                confidence=group.confidence * 0.9,  # Slightly lower confidence for subgroups
                metadata={
                    'parent_group': group.group_id,
                    'split_strategy': result['strategy'],
                    'pattern': result.get('pattern')
                }
            )
            subgroups.append(subgroup)
        return subgroups
    
    def split_group_intelligently(self, group: FunctionGroup, recursive=True) -> List[FunctionGroup]:
        """Split a large group into smaller, more manageable subgroups."""
        if not self.should_split(group):
            return [group]
        
        strategy = self.recommend_split_strategy(group)
        split_results = self.strategy_manager.apply_strategy(group, strategy)
        subgroups = self._create_subgroups_from_split_results(group, split_results)
        
        # Handle recursive splitting for large "Other" groups
        if recursive:
            final_subgroups = []
            for subgroup in subgroups:
                if self.should_split(subgroup) and "Other" in subgroup.label:
                    # Recursively split the large "Other" group
                    recursive_subgroups = self.split_group_intelligently(subgroup, recursive=False)
                    final_subgroups.extend(recursive_subgroups)
                else:
                    final_subgroups.append(subgroup)
            return final_subgroups
        
        return subgroups
    
    def calculate_split_metrics(self, original_groups: List[FunctionGroup], split_groups: List[FunctionGroup]) -> Dict[str, Any]:
        """Calculate metrics about the splitting operation."""
        original_sizes = [len(g.functions) for g in original_groups]
        split_sizes = [len(g.functions) for g in split_groups]
        
        return {
            'original_groups': len(original_groups),
            'split_groups': len(split_groups),
            'largest_original': max(original_sizes) if original_sizes else 0,
            'largest_split': max(split_sizes) if split_sizes else 0,
            'average_original': sum(original_sizes) / len(original_sizes) if original_sizes else 0,
            'average_split': sum(split_sizes) / len(split_sizes) if split_sizes else 0,
            'groups_over_20': sum(1 for s in split_sizes if s > 20),
            'groups_under_15': sum(1 for s in split_sizes if s <= 15),
            'splitting_factor': len(split_groups) / len(original_groups) if original_groups else 0
        }
    
    
    async def split_large_groups_with_llm(self, groups: List[FunctionGroup], max_depth: int = 3, current_depth: int = 0) -> List[FunctionGroup]:
        """Split groups larger than threshold using LLM-generated rules.
        
        Args:
            groups: Groups to split
            max_depth: Maximum recursion depth to prevent infinite loops
            current_depth: Current recursion depth
        """
        # Prevent infinite recursion
        if current_depth >= max_depth:
            self.logger.warning(f"Maximum split depth {max_depth} reached, stopping further splits")
            return groups
        
        result_groups = []
        
        # Apply existing rules first
        try:
            all_rules = self.rule_repository.get_all_rules()
        except Exception as e:
            self.logger.error(f"Failed to retrieve existing rules: {e}")
            # DBエラーでも処理を継続（新規ルールを生成）
            all_rules = []
        
        for group in groups:
            # Check if group has already been split enough
            if self.split_coordinator.should_skip_group(group, max_depth):
                result_groups.append(group)
                continue
                
            split_count = group.metadata.get('split_count', 0)
            
            if len(group.functions) <= self.llm_group_threshold:
                result_groups.append(group)
                continue
            
            # Try existing rules
            split_successful = False
            for rule in all_rules:
                try:
                    is_valid, matched, unmatched = self.llm_service.validate_split_pattern(group, rule.pattern)
                    if is_valid:
                        # Create subgroups with incremented split count
                        group_a, group_b = self.split_coordinator.create_rule_based_groups(
                            group, matched, unmatched, rule, split_count
                        )
                        
                        # Recursively split if still too large
                        sub_results_a = await self.split_large_groups_with_llm([group_a], max_depth, current_depth + 1)
                        sub_results_b = await self.split_large_groups_with_llm([group_b], max_depth, current_depth + 1)
                        result_groups.extend(sub_results_a)
                        result_groups.extend(sub_results_b)
                        
                        self.rule_repository.update_rule_stats(rule.pattern, True)
                        split_successful = True
                        break
                except Exception as e:
                    self.logger.warning(f"Failed to apply rule '{rule.pattern}': {e}")
                    continue
            
            if split_successful:
                continue
            
            # Generate new rule with LLM
            max_attempts = 3
            for attempt in range(max_attempts):
                # Sample functions (5 or all if less)
                sample_size = min(5, len(group.functions))
                sample_functions = random.sample(group.functions, sample_size)
                
                try:
                    pattern, reasoning, group_a_name, group_b_name = await self.llm_service.generate_split_pattern(sample_functions)
                    is_valid, matched, unmatched = self.llm_service.validate_split_pattern(group, pattern)
                    
                    if is_valid:
                        # Save new rule
                        new_rule = SplitRule(
                            pattern=pattern,
                            reasoning=reasoning,
                            created_at=datetime.now()
                        )
                        
                        try:
                            self.rule_repository.save_rule(new_rule)
                        except Exception as e:
                            self.logger.warning(f"Failed to save rule to DB: {e}")
                            # ルール保存失敗でも分割処理は継続
                        
                        # Create subgroups with meaningful names and incremented split count
                        split_info = {
                            'pattern': pattern,
                            'reasoning': reasoning,
                            'group_a_name': group_a_name,
                            'group_b_name': group_b_name,
                            'matched_functions': matched,
                            'unmatched_functions': unmatched
                        }
                        group_a, group_b = self.split_coordinator.create_llm_based_groups(
                            group, split_info, split_count
                        )
                        
                        # Recursively split if still too large
                        sub_results_a = await self.split_large_groups_with_llm([group_a], max_depth, current_depth + 1)
                        sub_results_b = await self.split_large_groups_with_llm([group_b], max_depth, current_depth + 1)
                        result_groups.extend(sub_results_a)
                        result_groups.extend(sub_results_b)
                        
                        self.logger.info(f"Successfully split group {group.group_id} with LLM rule: {pattern}")
                        break
                    else:
                        self.logger.warning(f"Generated pattern '{pattern}' did not create valid split")
                    
                except RuntimeError as e:
                    self.logger.error(f"Attempt {attempt + 1} failed with error: {e}")
                    if attempt == max_attempts - 1:
                        # 最後の試行でもエラーの場合は上位に伝播
                        raise RuntimeError(f"Cannot split group {group.group_id}: {e}")
                except Exception as e:
                    self.logger.error(f"Unexpected error in attempt {attempt + 1}: {e}")
                    if attempt == max_attempts - 1:
                        raise RuntimeError(f"Unexpected error splitting group {group.group_id}: {e}")
                    
                if attempt == max_attempts - 1:
                    # Failed to split after all attempts
                    error_msg = f"Failed to split group {group.group_id} after {max_attempts} attempts"
                    self.logger.error(error_msg)
                    raise RuntimeError(error_msg)
        
        return result_groups


async def demo_llm_splitting():
    """Demo the LLM-based group splitting functionality."""
    print("🤖 LLM-based Smart Group Splitter Demo")
    print("=" * 50)
    
    # Create a mock large group
    mock_functions = []
    
    # Generate 150 diverse functions
    patterns = [
        ('validate_', 'email|password|input|data|format'),
        ('process_', 'data|request|response|file|image'),
        ('handle_', 'error|exception|request|event|callback'),
        ('calculate_', 'total|average|sum|percentage|score'),
        ('test_', 'unit|integration|api|validation|performance'),
        ('get_', 'user|data|config|status|info'),
        ('set_', 'value|config|state|property|attribute'),
        ('create_', 'object|instance|file|connection|resource'),
        ('update_', 'record|status|data|cache|database'),
        ('delete_', 'file|record|cache|temp|resource')
    ]
    
    for prefix, suffixes in patterns:
        suffix_list = suffixes.split('|')
        for i in range(15):  # 15 functions per pattern
            suffix = suffix_list[i % len(suffix_list)]
            mock_functions.append({
                'name': f"{prefix}{suffix}_{i}",
                'code': f"def {prefix}{suffix}_{i}():\n    # {prefix} operation\n    pass",
                'file_path': f"module_{prefix.strip('_')}.py"
            })
    
    large_group = FunctionGroup(
        group_id="mixed_functions",
        functions=mock_functions,
        label="Mixed Functions",
        confidence=0.7,
        metadata={}
    )
    
    # Initialize splitter with AI
    splitter = SmartGroupSplitter(enable_ai=True)
    
    print(f"Original group: {large_group.label} ({len(large_group.functions)} functions)")
    print(f"Threshold for LLM splitting: {splitter.llm_group_threshold} functions")
    
    # Perform LLM-based splitting
    result_groups = await splitter.split_large_groups_with_llm([large_group])
    
    print(f"\nSplit into {len(result_groups)} groups:")
    for i, group in enumerate(result_groups, 1):
        print(f"  {i}. {group.label}: {len(group.functions)} functions")
        if 'split_reason' in group.metadata:
            print(f"     Reason: {group.metadata['split_reason'][:50]}...")
    
    # Show saved rules
    rules = splitter.rule_repository.get_all_rules()
    if rules:
        print(f"\n📝 Generated Split Rules ({len(rules)} total):")
        for rule in rules[:3]:  # Show first 3 rules
            print(f"  Pattern: {rule.pattern}")
            print(f"  Reasoning: {rule.reasoning[:60]}...")
            print()


def demo_smart_splitting():
    """Demo the smart group splitting functionality."""
    print("🔪 Smart Group Splitter Demo")
    print("=" * 40)
    
    # Create a mock large setter group
    mock_setters = []
    setter_patterns = [
        ('set_config_value', 'config'),
        ('set_user_state', 'state'),
        ('update_profile', 'update'),
        ('save_to_database', 'save'),
        ('write_to_file', 'write'),
        ('register_handler', 'register'),
        ('apply_changes', 'apply')
    ]
    
    # Generate mock functions
    for base_name, category in setter_patterns:
        for i in range(20):  # 20 functions per pattern = 140 total
            mock_setters.append({
                'name': f"{base_name}_{i}",
                'category': category,
                'file_path': f"module_{category}.py"
            })
    
    large_group = FunctionGroup(
        group_id="setters_main",
        functions=mock_setters[:129],  # Simulate the actual 129 setter functions
        label="Setter Functions",
        confidence=0.6,
        metadata={}
    )
    
    # Split the group
    splitter = SmartGroupSplitter()
    
    print(f"Original group: {large_group.label} ({len(large_group.functions)} functions)")
    print(f"Should split: {splitter.should_split(large_group)}")
    
    # Perform splitting
    subgroups = splitter.split_group_intelligently(large_group)
    
    print(f"\nSplit into {len(subgroups)} subgroups:")
    for i, subgroup in enumerate(subgroups, 1):
        print(f"  {i}. {subgroup.label}: {len(subgroup.functions)} functions")
    
    # Calculate metrics
    metrics = splitter.calculate_split_metrics([large_group], subgroups)
    print(f"\nSplitting metrics:")
    print(f"  Largest group reduced from {metrics['largest_original']} to {metrics['largest_split']}")
    print(f"  Average group size: {metrics['average_original']:.1f} → {metrics['average_split']:.1f}")
    print(f"  Groups ≤15 functions: {metrics['groups_under_15']}/{metrics['split_groups']}")


if __name__ == "__main__":
    import asyncio
    # Run async demo
    asyncio.run(demo_llm_splitting())
    # Run sync demo
    demo_smart_splitting()