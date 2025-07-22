"""
Split Strategy Manager - Manages function group splitting strategies.
Extracted from SmartGroupSplitter to separate concerns.
"""

import re
from typing import List, Dict, Tuple
from dataclasses import dataclass
from .function_group_clustering import FunctionGroup


@dataclass
class SplitStrategy:
    """Predefined split strategies for common function patterns."""
    name: str
    patterns: List[Tuple[str, str]]  # (pattern, label) pairs
    description: str


class SplitStrategyManager:
    """Manages splitting strategies for function groups."""
    
    # Predefined splitting strategies
    SETTER_STRATEGY = SplitStrategy(
        name="setter_subdivision",
        patterns=[
            (r'^__init__$|^__post_init__$', "Constructor/Initializers"),
            (r'set_config|config_set|configure', "Configuration Setters"),
            (r'set_state|state_set|update_state', "State Management"),
            (r'update_(?!state)', "Update Operations"),
            (r'save_|persist_|store_', "Persistence Operations"),
            (r'write_|dump_|export_', "File Writers"),
            (r'load_|read_|import_', "Data Loaders"),
            (r'assign_|bind_|attach_', "Assignment Operations"),
            (r'init(?:ialize)?_|setup_', "Initialization"),
            (r'register_|add_|append_', "Registration Operations"),
            (r'remove_|delete_|clear_', "Removal Operations"),
            (r'reset_|restore_|revert_', "Reset Operations"),
            (r'enable_|disable_|toggle_', "Toggle Operations"),
            (r'modify_|change_|alter_', "Modification Operations"),
            (r'create_|make_|build_', "Creation Operations"),
            (r'apply_|set_(?!config|state)', "General Setters"),
        ],
        description="Subdivide setter functions by operation type"
    )
    
    GETTER_STRATEGY = SplitStrategy(
        name="getter_subdivision",
        patterns=[
            (r'get_config|config_get|configuration', "Configuration Getters"),
            (r'get_state|state_get|current_state', "State Getters"),
            (r'get_data|fetch_data|retrieve_data', "Data Retrievers"),
            (r'get_.*_list|list_|all_', "Collection Getters"),
            (r'is_|has_|can_|should_', "Boolean Getters"),
            (r'find_|search_|locate_', "Search Operations"),
            (r'calculate_|compute_|derive_', "Computed Properties"),
            (r'__get|property|cached_property', "Property Getters"),
            (r'get_', "General Getters"),
        ],
        description="Subdivide getter functions by return type and purpose"
    )
    
    BUSINESS_LOGIC_STRATEGY = SplitStrategy(
        name="business_logic_subdivision",
        patterns=[
            (r'process_|handle_', "Processing Logic"),
            (r'analyze_|inspect_|examine_', "Analysis Logic"),
            (r'calculate_|compute_', "Calculation Logic"),
            (r'validate_|verify_|check_', "Validation Logic"),
            (r'transform_|convert_|parse_', "Transformation Logic"),
            (r'generate_|create_|build_', "Generation Logic"),
            (r'orchestrate_|coordinate_|manage_', "Orchestration Logic"),
            (r'optimize_|improve_|enhance_', "Optimization Logic"),
            (r'.*', "General Business Logic"),
        ],
        description="Subdivide business logic by operation type"
    )
    
    def __init__(self):
        self.strategies = {
            'setter': self.SETTER_STRATEGY,
            'getter': self.GETTER_STRATEGY,
            'business_logic': self.BUSINESS_LOGIC_STRATEGY,
        }
    
    def recommend_strategy(self, group: FunctionGroup) -> SplitStrategy:
        """Recommend appropriate split strategy based on group type."""
        label_lower = group.label.lower()
        
        if 'setter' in label_lower:
            return self.strategies['setter']
        elif 'getter' in label_lower:
            return self.strategies['getter']
        elif 'business' in label_lower or 'logic' in label_lower:
            return self.strategies['business_logic']
        else:
            # Default: split by common prefixes
            return self._create_prefix_strategy(group)
    
    def _create_prefix_strategy(self, group: FunctionGroup) -> SplitStrategy:
        """Create a splitting strategy based on common prefixes."""
        # Analyze function names to find common prefixes
        prefix_counts = {}
        for func in group.functions:
            name = func.get('name', '')
            # Extract prefix (first word before _)
            parts = name.split('_')
            if len(parts) > 1:
                prefix = parts[0]
                prefix_counts[prefix] = prefix_counts.get(prefix, 0) + 1
        
        # Sort prefixes by frequency
        common_prefixes = sorted(prefix_counts.items(), key=lambda x: x[1], reverse=True)
        
        # Create patterns for top prefixes
        patterns = []
        for prefix, count in common_prefixes[:8]:  # Top 8 prefixes
            if count >= 3:  # At least 3 functions with this prefix
                pattern = f'^{prefix}_'
                label = f"{prefix.title()} Operations"
                patterns.append((pattern, label))
        
        # Add catch-all
        patterns.append((r'.*', f"Other {group.label}"))
        
        return SplitStrategy(
            name=f"{group.label.lower()}_prefix_split",
            patterns=patterns,
            description=f"Split {group.label} by function prefix"
        )
    
    def apply_strategy(self, group: FunctionGroup, strategy: SplitStrategy) -> List[Dict]:
        """Apply a strategy to split a group, returning split results."""
        split_results = []
        remaining_functions = group.functions.copy()
        
        for pattern, label in strategy.patterns:
            if not remaining_functions:
                break
                
            matched_functions = []
            unmatched_functions = []
            
            for func in remaining_functions:
                func_name = func.get('name', '').lower()
                if re.search(pattern, func_name):
                    matched_functions.append(func)
                else:
                    unmatched_functions.append(func)
            
            if matched_functions and len(matched_functions) >= 3:  # Minimum viable group
                split_results.append({
                    'functions': matched_functions,
                    'label': f"{label} ({group.label})",
                    'pattern': pattern,
                    'strategy': strategy.name
                })
                remaining_functions = unmatched_functions
        
        # Handle remaining functions
        if remaining_functions and len(remaining_functions) >= 3:
            split_results.append({
                'functions': remaining_functions,
                'label': f"Other {group.label}",
                'pattern': None,
                'strategy': strategy.name
            })
        elif remaining_functions and split_results:
            # Add to the smallest existing subgroup
            smallest_idx = min(range(len(split_results)), 
                             key=lambda i: len(split_results[i]['functions']))
            split_results[smallest_idx]['functions'].extend(remaining_functions)
        
        return split_results