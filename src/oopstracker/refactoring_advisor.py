"""
Refactoring Advisor - Provides concrete refactoring suggestions based on function groups.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from .function_group_clustering import FunctionGroup


class RefactoringPattern(Enum):
    """Refactoring patterns based on the YAML definition."""
    EXTRACT = "Extract"
    INLINE = "Inline"
    UNIFY = "Unify"
    ENCAPSULATE = "Encapsulate"
    CENTRALIZE = "Centralize"
    ISOLATE = "Isolate"
    PROMOTE = "Promote"
    DEMOTE = "Demote"
    BRIDGE = "Bridge"
    LAYER = "Layer"


@dataclass
class RefactoringProposal:
    """A concrete refactoring proposal."""
    pattern: RefactoringPattern
    target_group: FunctionGroup
    title: str
    description: str
    impact: str  # "high", "medium", "low"
    effort: str  # "high", "medium", "low"
    example_code: Optional[str] = None
    steps: List[str] = None


class RefactoringAdvisor:
    """Analyzes function groups and provides actionable refactoring suggestions."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Pattern descriptions
        self.pattern_descriptions = {
            RefactoringPattern.EXTRACT: "複雑なロジックを関数・クラスに切り出す",
            RefactoringPattern.INLINE: "抽象化しすぎた処理を戻す・埋める",
            RefactoringPattern.UNIFY: "異なる処理/インタフェースを統一",
            RefactoringPattern.ENCAPSULATE: "実装の詳細を隠蔽し、明確なAPIにする",
            RefactoringPattern.CENTRALIZE: "分散したロジックを共通層に集約",
            RefactoringPattern.ISOLATE: "外部依存や副作用を切り離す",
            RefactoringPattern.PROMOTE: "局所処理を共通化や上位に昇格",
            RefactoringPattern.DEMOTE: "汎用処理を限定的な場所に移す",
            RefactoringPattern.BRIDGE: "実装の違いを抽象層でつなぐ",
            RefactoringPattern.LAYER: "層構造で責務を整理"
        }
    
    def analyze_groups_and_propose(self, function_groups: List[FunctionGroup]) -> List[RefactoringProposal]:
        """Analyze function groups and generate refactoring proposals."""
        proposals = []
        
        for group in function_groups:
            # Skip small groups
            if len(group.functions) < 5:
                continue
            
            # Analyze group characteristics
            group_proposals = self._analyze_single_group(group)
            proposals.extend(group_proposals)
        
        # Sort by impact and effort
        proposals.sort(key=lambda p: (
            self._impact_score(p.impact),
            -self._effort_score(p.effort)
        ), reverse=True)
        
        return proposals
    
    def _analyze_single_group(self, group: FunctionGroup) -> List[RefactoringProposal]:
        """Analyze a single function group for refactoring opportunities."""
        proposals = []
        
        # Check for setter pattern
        if self._is_setter_group(group):
            proposals.extend(self._propose_setter_refactoring(group))
        
        # Check for getter pattern
        elif self._is_getter_group(group):
            proposals.extend(self._propose_getter_refactoring(group))
        
        # Check for similar business logic
        elif self._is_business_logic_group(group):
            proposals.extend(self._propose_business_logic_refactoring(group))
        
        # General large group handling
        if len(group.functions) > 20:
            proposals.append(self._propose_layer_refactoring(group))
        
        return proposals
    
    def _is_setter_group(self, group: FunctionGroup) -> bool:
        """Check if this is a setter function group."""
        label_lower = group.label.lower()
        return any(keyword in label_lower for keyword in ['setter', 'set', 'update', 'save'])
    
    def _is_getter_group(self, group: FunctionGroup) -> bool:
        """Check if this is a getter function group."""
        label_lower = group.label.lower()
        return any(keyword in label_lower for keyword in ['getter', 'get', 'fetch', 'load'])
    
    def _is_business_logic_group(self, group: FunctionGroup) -> bool:
        """Check if this is a business logic group."""
        label_lower = group.label.lower()
        return any(keyword in label_lower for keyword in ['business', 'logic', 'process', 'calculate'])
    
    def _propose_setter_refactoring(self, group: FunctionGroup) -> List[RefactoringProposal]:
        """Propose refactoring for setter functions."""
        proposals = []
        
        # Extract common validation
        if len(group.functions) > 10:
            proposals.append(RefactoringProposal(
                pattern=RefactoringPattern.EXTRACT,
                target_group=group,
                title=f"Extract validation logic from {len(group.functions)} setters",
                description="Many setter functions likely have similar validation. Extract common validation into a shared function.",
                impact="high",
                effort="medium",
                example_code='''# Before:
def set_user_name(name):
    if not name or len(name) > 100:
        raise ValueError("Invalid name")
    user.name = name

def set_user_email(email):
    if not email or "@" not in email:
        raise ValueError("Invalid email")
    user.email = email

# After:
def validate_field(value, field_type):
    validators = {
        "name": lambda v: v and len(v) <= 100,
        "email": lambda v: v and "@" in v
    }
    if not validators[field_type](value):
        raise ValueError(f"Invalid {field_type}")
    return value

def set_user_name(name):
    user.name = validate_field(name, "name")

def set_user_email(email):
    user.email = validate_field(email, "email")''',
                steps=[
                    "Identify common validation patterns across setters",
                    "Create a centralized validation function or class",
                    "Refactor setters to use the shared validation",
                    "Add unit tests for the validation logic"
                ]
            ))
        
        # Unify interface
        if len(group.functions) > 15:
            proposals.append(RefactoringProposal(
                pattern=RefactoringPattern.UNIFY,
                target_group=group,
                title=f"Unify {len(group.functions)} setter interfaces",
                description="Create a consistent interface for all setter operations.",
                impact="medium",
                effort="high",
                steps=[
                    "Define a common setter interface or base class",
                    "Standardize parameter names and return types",
                    "Implement error handling consistently",
                    "Update all callers to use the new interface"
                ]
            ))
        
        return proposals
    
    def _propose_getter_refactoring(self, group: FunctionGroup) -> List[RefactoringProposal]:
        """Propose refactoring for getter functions."""
        proposals = []
        
        # Centralize data access
        if len(group.functions) > 10:
            proposals.append(RefactoringProposal(
                pattern=RefactoringPattern.CENTRALIZE,
                target_group=group,
                title=f"Centralize data access for {len(group.functions)} getters",
                description="Create a data access layer to handle all getter operations.",
                impact="high",
                effort="medium",
                example_code='''# Create a DataAccessLayer class
class DataAccessLayer:
    def get(self, entity_type, field, filter_criteria=None):
        # Centralized logic for all getters
        pass''',
                steps=[
                    "Create a DataAccessLayer class",
                    "Move common query logic into the layer",
                    "Add caching capabilities",
                    "Refactor getters to use the new layer"
                ]
            ))
        
        return proposals
    
    def _propose_business_logic_refactoring(self, group: FunctionGroup) -> List[RefactoringProposal]:
        """Propose refactoring for business logic functions."""
        proposals = []
        
        # Layer the logic
        if len(group.functions) > 8:
            proposals.append(RefactoringProposal(
                pattern=RefactoringPattern.LAYER,
                target_group=group,
                title=f"Layer {len(group.functions)} business logic functions",
                description="Organize business logic into clear layers (service, domain, repository).",
                impact="high",
                effort="high",
                steps=[
                    "Identify different responsibility levels",
                    "Create service layer for orchestration",
                    "Create domain layer for business rules",
                    "Create repository layer for data access",
                    "Move functions to appropriate layers"
                ]
            ))
        
        return proposals
    
    def _propose_layer_refactoring(self, group: FunctionGroup) -> RefactoringProposal:
        """Propose layer refactoring for large groups."""
        return RefactoringProposal(
            pattern=RefactoringPattern.LAYER,
            target_group=group,
            title=f"Split {len(group.functions)} functions into layers",
            description="This group is too large. Organize into logical layers or modules.",
            impact="high",
            effort="high",
            steps=[
                "Analyze function dependencies",
                "Identify logical boundaries",
                "Create module structure",
                "Move functions to appropriate modules",
                "Update imports and dependencies"
            ]
        )
    
    def _impact_score(self, impact: str) -> int:
        """Convert impact to numeric score."""
        return {"high": 3, "medium": 2, "low": 1}.get(impact, 0)
    
    def _effort_score(self, effort: str) -> int:
        """Convert effort to numeric score."""
        return {"high": 3, "medium": 2, "low": 1}.get(effort, 0)
    
    def format_proposals_for_display(self, proposals: List[RefactoringProposal]) -> str:
        """Format proposals for CLI display."""
        if not proposals:
            return "No refactoring opportunities found for groups with 5+ functions."
        
        lines = ["", "🔧 Refactoring Proposals (sorted by impact/effort ratio):", ""]
        
        for i, proposal in enumerate(proposals[:5], 1):  # Show top 5
            lines.append(f"{i}. {proposal.title}")
            lines.append(f"   Pattern: {proposal.pattern.value} - {self.pattern_descriptions[proposal.pattern]}")
            lines.append(f"   Impact: {proposal.impact} | Effort: {proposal.effort}")
            lines.append(f"   {proposal.description}")
            
            if proposal.steps:
                lines.append("   Steps:")
                for j, step in enumerate(proposal.steps, 1):
                    lines.append(f"     {j}. {step}")
            
            lines.append("")
        
        if len(proposals) > 5:
            lines.append(f"   ... and {len(proposals) - 5} more proposals")
        
        return "\n".join(lines)