"""Bridge for semantic analysis functionality."""

import asyncio
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
from dataclasses import dataclass
import logging

from ..models import CodeRecord
from ..semantic_analysis_coordinator import SemanticAnalysisCoordinator


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


class SemanticAnalysisBridge:
    """Bridge to semantic analysis functionality."""
    
    def __init__(self, intent_unified_available: bool = True):
        """Initialize semantic analysis bridge."""
        self.coordinator = SemanticAnalysisCoordinator(intent_unified_available)
        self.logger = logging.getLogger(__name__)
        self._semantic_timeout = 30.0
        
    async def initialize(self) -> None:
        """Initialize semantic analysis components."""
        await self.coordinator.initialize()
        
    async def analyze(
        self,
        code_records: List[CodeRecord],
        structural_candidates: List[Tuple[CodeRecord, CodeRecord, float]],
        threshold: float = 0.7,
        max_concurrent: int = 3,
        intent_tree_adapter: Any = None
    ) -> List[SemanticDuplicateResult]:
        """Analyze semantic duplicates for structural candidates.
        
        Args:
            code_records: All code records
            structural_candidates: Structural duplicate candidates
            threshold: Semantic similarity threshold
            max_concurrent: Maximum concurrent analyses
            intent_tree_adapter: Optional intent tree adapter
            
        Returns:
            List of semantic duplicate results
        """
        # Convert candidates to code pairs
        code_pairs = self._prepare_code_pairs(structural_candidates[:20])
        
        if not code_pairs:
            return []
        
        # Perform analysis
        results = await self._analyze_pairs(
            code_pairs, 
            max_concurrent, 
            intent_tree_adapter
        )
        
        # Filter by threshold
        return [r for r in results if r.semantic_similarity >= threshold]
    
    def _prepare_code_pairs(
        self, 
        candidates: List[Tuple[CodeRecord, CodeRecord, float]]
    ) -> List[Tuple[str, str, Tuple[CodeRecord, CodeRecord, float]]]:
        """Prepare code pairs for analysis."""
        code_pairs = []
        for candidate in candidates:
            try:
                code1 = self._normalize_code_indentation(candidate[0].code_content)
                code2 = self._normalize_code_indentation(candidate[1].code_content)
                code_pairs.append((code1, code2, candidate))
            except (AttributeError, IndexError):
                continue
        return code_pairs
    
    def _normalize_code_indentation(self, code: str) -> str:
        """Normalize code indentation."""
        if not code:
            return code
            
        lines = code.split('\n')
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
    
    async def _analyze_pairs(
        self,
        code_pairs: List[Tuple[str, str, Tuple[CodeRecord, CodeRecord, float]]],
        max_concurrent: int,
        intent_tree_adapter: Any
    ) -> List[SemanticDuplicateResult]:
        """Analyze code pairs concurrently."""
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def analyze_pair(code1, code2, candidate):
            async with semaphore:
                return await self._analyze_single_pair(
                    code1, code2, candidate, intent_tree_adapter
                )
        
        tasks = [analyze_pair(c1, c2, cand) for c1, c2, cand in code_pairs]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter successful results
        return [r for r in results if isinstance(r, SemanticDuplicateResult)]
    
    async def _analyze_single_pair(
        self,
        code1: str,
        code2: str,
        candidate: Tuple[CodeRecord, CodeRecord, float],
        intent_tree_adapter: Any
    ) -> Optional[SemanticDuplicateResult]:
        """Analyze a single code pair."""
        try:
            start_time = asyncio.get_event_loop().time()
            
            result = await self.coordinator.analyze_semantic_similarity(
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
    
    async def quick_check(
        self, 
        code1: str, 
        code2: str, 
        language: str = "python",
        intent_tree_adapter: Any = None
    ) -> Dict[str, Any]:
        """Quick semantic similarity check."""
        return await self.coordinator.analyze_semantic_similarity(
            code1, code2, language, intent_tree_adapter
        )