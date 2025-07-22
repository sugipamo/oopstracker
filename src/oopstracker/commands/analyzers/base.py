"""
Base analyzer class for all analysis components.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass


@dataclass
class AnalysisResult:
    """Result of an analysis operation."""
    success: bool
    data: Dict[str, Any]
    summary: str
    errors: List[str] = None
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []


class BaseAnalyzer(ABC):
    """Base class for all analyzers."""
    
    def __init__(self, context: Any):
        """Initialize analyzer with command context."""
        self.context = context
        self.args = context.args
        self.detector = context.detector
        self.semantic_detector = context.semantic_detector
        
    @abstractmethod
    async def analyze(self, **kwargs) -> AnalysisResult:
        """Perform the analysis and return results."""
        pass
    
    @abstractmethod
    def display_results(self, result: AnalysisResult) -> None:
        """Display analysis results to the user."""
        pass
    
    def format_file_path(self, path: str) -> str:
        """Format file path for display."""
        if hasattr(self.args, 'relative_paths') and self.args.relative_paths:
            from pathlib import Path
            try:
                return str(Path(path).relative_to(Path.cwd()))
            except ValueError:
                return path
        return path