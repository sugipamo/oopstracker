"""Semantic analysis component for duplicate detection."""

import asyncio
import logging
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum

from ..models import CodeRecord
from ..semantic_analysis_coordinator import SemanticAnalysisCoordinator
from ..intent_tree_fixed_adapter import FixedIntentTreeAdapter


class SemanticAnalysisStatus(Enum):
    """Status of semantic analysis."""
    SUCCESS = "success"
    TIMEOUT = "timeout"
    ERROR = "error"
    UNAVAILABLE = "unavailable"


@dataclass
class SemanticDuplicateResult:
    """Result of semantic duplicate detection."""
    code_record_1: CodeRecord
    code_record_2: CodeRecord
    semantic_similarity: float
    confidence: float
    analysis_method: str
    reasoning: str
    analysis_time: float
    status: SemanticAnalysisStatus
    metadata: Dict[str, Any]


class SemanticAnalyzer:
    """Handle semantic duplicate analysis."""
    
    def __init__(self, semantic_coordinator: SemanticAnalysisCoordinator, 
                 intent_tree_adapter: FixedIntentTreeAdapter,
                 semantic_timeout: float = 30.0):
        """Initialize semantic analyzer."""
        self.logger = logging.getLogger(__name__)
        self.semantic_coordinator = semantic_coordinator
        self.intent_tree_adapter = intent_tree_adapter
        self._semantic_timeout = semantic_timeout
    
    async def analyze_duplicates(
        self,
        code_records: List[CodeRecord],
        structural_candidates: List[Tuple[CodeRecord, CodeRecord, float]],
        threshold: float,
        max_concurrent: int
    ) -> List[SemanticDuplicateResult]:
        """Analyze semantic duplicates for structural candidates."""
        
        # Convert structural candidates to code pairs
        code_pairs = []
        for candidate in structural_candidates[:20]:  # Limit to top 20 candidates
            try:
                # candidate is a tuple (CodeRecord, CodeRecord, float)
                code1 = self._normalize_code_indentation(candidate[0].code_content)
                code2 = self._normalize_code_indentation(candidate[1].code_content)
                code_pairs.append((code1, code2, candidate))
            except (AttributeError, IndexError):
                # Handle different candidate structures
                continue
        
        if not code_pairs:
            return []
        
        # Perform semantic analysis
        semantic_results = []
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def analyze_pair(code1: str, code2: str, candidate: Tuple[CodeRecord, CodeRecord, float]) -> Optional[SemanticDuplicateResult]:
            async with semaphore:
                try:
                    start_time = asyncio.get_event_loop().time()
                    
                    result = await self.semantic_coordinator.analyze_semantic_similarity(
                        code1, code2, intent_tree_adapter=self.intent_tree_adapter
                    )
                    
                    analysis_time = asyncio.get_event_loop().time() - start_time
                    
                    return SemanticDuplicateResult(
                        code_record_1=candidate[0],
                        code_record_2=candidate[1],
                        semantic_similarity=result.get("similarity", 0.0),
                        confidence=result.get("confidence", 0.0),
                        analysis_method=result.get("method", "unknown"),
                        reasoning=result.get("reasoning", ""),
                        analysis_time=analysis_time,
                        status=SemanticAnalysisStatus.SUCCESS,
                        metadata=result.get("details", {})
                    )
                    
                except asyncio.TimeoutError:
                    return SemanticDuplicateResult(
                        code_record_1=candidate[0],
                        code_record_2=candidate[1],
                        semantic_similarity=0.0,
                        confidence=0.0,
                        analysis_method="timeout",
                        reasoning="Analysis timed out",
                        analysis_time=self._semantic_timeout,
                        status=SemanticAnalysisStatus.TIMEOUT,
                        metadata={}
                    )
                except Exception as e:
                    return SemanticDuplicateResult(
                        code_record_1=candidate[0],
                        code_record_2=candidate[1],
                        semantic_similarity=0.0,
                        confidence=0.0,
                        analysis_method="error",
                        reasoning=f"Analysis failed: {str(e)}",
                        analysis_time=0.0,
                        status=SemanticAnalysisStatus.ERROR,
                        metadata={"error": str(e)}
                    )
        
        # Execute all analyses
        tasks = [analyze_pair(code1, code2, candidate) for code1, code2, candidate in code_pairs]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter successful results
        for result in results:
            if isinstance(result, SemanticDuplicateResult):
                semantic_results.append(result)
        
        # Filter by threshold
        filtered_results = [
            result for result in semantic_results
            if result.semantic_similarity >= threshold
        ]
        
        return filtered_results
    
    def _normalize_code_indentation(self, code: str) -> str:
        """Normalize code indentation for comparison."""
        if not code:
            return ""
        
        lines = code.split('\n')
        if not lines:
            return code
        
        # Find minimum indentation (excluding empty lines)
        min_indent = float('inf')
        for line in lines:
            stripped = line.lstrip()
            if stripped:  # Non-empty line
                indent = len(line) - len(stripped)
                min_indent = min(min_indent, indent)
        
        if min_indent == float('inf'):
            return code
        
        # Remove minimum indentation from all lines
        normalized_lines = []
        for line in lines:
            if line.strip():  # Non-empty line
                normalized_lines.append(line[min_indent:])
            else:
                normalized_lines.append('')
        
        return '\n'.join(normalized_lines)