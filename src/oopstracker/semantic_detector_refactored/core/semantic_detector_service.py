"""Semantic duplicate detection service."""

import asyncio
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

from ...models import CodeRecord
from ...semantic_analysis_coordinator import SemanticAnalysisCoordinator


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


class SemanticDetectorService:
    """Service for detecting semantic duplicates in code."""
    
    def __init__(self, intent_unified_available: bool = True):
        """Initialize semantic detector service.
        
        Args:
            intent_unified_available: Whether intent_unified service is available
        """
        self.logger = logging.getLogger(__name__)
        self.semantic_coordinator = SemanticAnalysisCoordinator(intent_unified_available)
        self._semantic_timeout = 30.0  # Default timeout for semantic analysis
    
    async def initialize(self) -> None:
        """Initialize semantic analysis components."""
        await self.semantic_coordinator.initialize()
    
    async def cleanup(self) -> None:
        """Cleanup semantic analysis resources."""
        # Semantic coordinator handles its own cleanup
        pass
    
    async def analyze_duplicates(
        self,
        code_records: List[CodeRecord],
        structural_candidates: List[Tuple[CodeRecord, CodeRecord, float]],
        threshold: float = 0.7,
        max_concurrent: int = 3,
        intent_tree_adapter: Optional[Any] = None
    ) -> List[SemanticDuplicateResult]:
        """Analyze semantic duplicates for structural candidates.
        
        Args:
            code_records: All code records being analyzed
            structural_candidates: Candidates from structural analysis
            threshold: Similarity threshold for semantic duplicates
            max_concurrent: Maximum concurrent analyses
            intent_tree_adapter: Optional intent tree adapter for enhanced analysis
            
        Returns:
            List of semantic duplicate results
        """
        # Convert structural candidates to code pairs
        code_pairs = self._prepare_code_pairs(structural_candidates)
        
        if not code_pairs:
            return []
        
        # Perform semantic analysis
        semantic_results = await self._analyze_code_pairs(
            code_pairs,
            max_concurrent,
            intent_tree_adapter
        )
        
        # Filter by threshold
        filtered_results = [
            result for result in semantic_results
            if result.semantic_similarity >= threshold
        ]
        
        return filtered_results
    
    async def quick_check(
        self,
        code1: str,
        code2: str,
        language: str = "python",
        intent_tree_adapter: Optional[Any] = None
    ) -> Dict[str, Any]:
        """Quick semantic similarity check for two code fragments.
        
        Args:
            code1: First code fragment
            code2: Second code fragment
            language: Programming language
            intent_tree_adapter: Optional intent tree adapter
            
        Returns:
            Semantic similarity analysis result
        """
        return await self.semantic_coordinator.analyze_semantic_similarity(
            code1, code2, language, intent_tree_adapter
        )
    
    def _prepare_code_pairs(
        self,
        structural_candidates: List[Tuple[CodeRecord, CodeRecord, float]],
        limit: int = 20
    ) -> List[Tuple[str, str, Tuple[CodeRecord, CodeRecord, float]]]:
        """Prepare code pairs for semantic analysis.
        
        Args:
            structural_candidates: Candidates from structural analysis
            limit: Maximum number of pairs to analyze
            
        Returns:
            List of code pairs with original candidate data
        """
        code_pairs = []
        
        for candidate in structural_candidates[:limit]:
            try:
                code1 = self._normalize_code_indentation(candidate[0].code_content)
                code2 = self._normalize_code_indentation(candidate[1].code_content)
                code_pairs.append((code1, code2, candidate))
            except (AttributeError, IndexError):
                continue
        
        return code_pairs
    
    def _normalize_code_indentation(self, code: str) -> str:
        """Normalize code indentation to ensure consistent analysis.
        
        Args:
            code: Code content to normalize
            
        Returns:
            Normalized code
        """
        # Basic normalization - can be enhanced
        lines = code.split('\n')
        # Remove common leading whitespace
        min_indent = float('inf')
        for line in lines:
            if line.strip():
                indent = len(line) - len(line.lstrip())
                min_indent = min(min_indent, indent)
        
        if min_indent == float('inf'):
            return code
        
        normalized_lines = []
        for line in lines:
            if line.strip():
                normalized_lines.append(line[min_indent:])
            else:
                normalized_lines.append(line)
        
        return '\n'.join(normalized_lines)
    
    async def _analyze_code_pairs(
        self,
        code_pairs: List[Tuple[str, str, Tuple[CodeRecord, CodeRecord, float]]],
        max_concurrent: int,
        intent_tree_adapter: Optional[Any]
    ) -> List[SemanticDuplicateResult]:
        """Analyze multiple code pairs concurrently.
        
        Args:
            code_pairs: List of code pairs to analyze
            max_concurrent: Maximum concurrent analyses
            intent_tree_adapter: Optional intent tree adapter
            
        Returns:
            List of semantic duplicate results
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def analyze_pair(
            code1: str,
            code2: str,
            candidate: Tuple[CodeRecord, CodeRecord, float]
        ) -> Optional[SemanticDuplicateResult]:
            async with semaphore:
                try:
                    start_time = asyncio.get_event_loop().time()
                    
                    result = await self.semantic_coordinator.analyze_semantic_similarity(
                        code1, code2, intent_tree_adapter=intent_tree_adapter
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
        tasks = [
            analyze_pair(code1, code2, candidate)
            for code1, code2, candidate in code_pairs
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter successful results
        semantic_results = []
        for result in results:
            if isinstance(result, SemanticDuplicateResult):
                semantic_results.append(result)
        
        return semantic_results