"""Semantic analysis service for code duplicate detection."""

import asyncio
import logging
import os
import sys
from typing import List, Optional, Tuple, Dict, Any
from dataclasses import dataclass
from enum import Enum

from ..models import CodeRecord


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


class SemanticAnalysisService:
    """Service for semantic code analysis and duplicate detection."""
    
    def __init__(self, intent_unified_available: bool = True):
        """Initialize semantic analysis service.
        
        Args:
            intent_unified_available: Whether intent_unified service is available
        """
        self.intent_unified_available = intent_unified_available
        self.logger = logging.getLogger(__name__)
        self._intent_unified_facade = None
        self._semantic_threshold = 0.7
        
    async def initialize(self) -> None:
        """Initialize semantic analysis components."""
        if self.intent_unified_available:
            try:
                # Dynamic import to avoid hard dependency
                intent_unified_path = os.path.join(
                    os.path.dirname(__file__), 
                    "../../../../intent/intent-unified/src"
                )
                if intent_unified_path not in sys.path:
                    sys.path.insert(0, intent_unified_path)
                
                from intent_unified.core.facade import IntentUnifiedFacade
                
                self._intent_unified_facade = IntentUnifiedFacade()
                await self._intent_unified_facade.__aenter__()
                
            except Exception as e:
                self.logger.warning(f"Failed to initialize semantic analysis: {e}")
                self.intent_unified_available = False
                self._intent_unified_facade = None
    
    async def cleanup(self) -> None:
        """Cleanup resources."""
        if self._intent_unified_facade:
            try:
                await self._intent_unified_facade.__aexit__(None, None, None)
            except Exception as e:
                self.logger.error(f"Error during semantic analyzer cleanup: {e}")
    
    async def analyze_duplicates(
        self,
        code_records: List[CodeRecord],
        structural_candidates: List[Tuple[CodeRecord, CodeRecord, float]],
        threshold: float = 0.7,
        max_concurrent: int = 3
    ) -> List[SemanticDuplicateResult]:
        """Analyze semantic duplicates for structural candidates.
        
        Args:
            code_records: List of all code records
            structural_candidates: Candidates from structural analysis
            threshold: Similarity threshold
            max_concurrent: Maximum concurrent analyses
            
        Returns:
            List of semantic duplicate results
        """
        if not self._intent_unified_facade:
            return []
        
        # Convert candidates to code pairs
        code_pairs = self._prepare_code_pairs(structural_candidates[:20])
        
        if not code_pairs:
            return []
        
        # Perform semantic analysis
        semantic_results = []
        semaphore = asyncio.Semaphore(max_concurrent)
        
        tasks = [
            self._analyze_pair(code1, code2, candidate, semaphore) 
            for code1, code2, candidate in code_pairs
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter successful results
        for result in results:
            if isinstance(result, SemanticDuplicateResult):
                semantic_results.append(result)
        
        # Filter by threshold
        return [
            result for result in semantic_results
            if result.semantic_similarity >= threshold
        ]
    
    async def quick_check(self, code1: str, code2: str, language: str = "python") -> Dict[str, Any]:
        """Quick semantic similarity check for two code fragments.
        
        Args:
            code1: First code fragment
            code2: Second code fragment
            language: Programming language
            
        Returns:
            Dictionary with similarity results
        """
        if not self.intent_unified_available or not self._intent_unified_facade:
            return {
                "available": False,
                "similarity": 0.0,
                "confidence": 0.0,
                "method": "unavailable",
                "reasoning": "Semantic analysis not available"
            }
        
        try:
            similarity = await self._intent_unified_facade.analyze_semantic_similarity(
                code1, code2, language=language
            )
            
            return {
                "available": True,
                "similarity": similarity.similarity_score,
                "confidence": similarity.confidence,
                "method": similarity.method.value,
                "reasoning": similarity.reasoning,
                "analysis_time": similarity.analysis_time
            }
        except Exception as e:
            return {
                "available": True,
                "similarity": 0.0,
                "confidence": 0.0,
                "method": "error",
                "reasoning": f"Analysis failed: {str(e)}",
                "error": str(e)
            }
    
    def _prepare_code_pairs(
        self, 
        structural_candidates: List[Tuple[CodeRecord, CodeRecord, float]]
    ) -> List[Tuple[str, str, Tuple[CodeRecord, CodeRecord, float]]]:
        """Prepare code pairs for semantic analysis."""
        code_pairs = []
        for candidate in structural_candidates:
            try:
                code1 = self._normalize_code_indentation(candidate[0].code_content)
                code2 = self._normalize_code_indentation(candidate[1].code_content)
                code_pairs.append((code1, code2, candidate))
            except (AttributeError, IndexError):
                continue
        return code_pairs
    
    async def _analyze_pair(
        self, 
        code1: str, 
        code2: str, 
        candidate: Tuple[CodeRecord, CodeRecord, float],
        semaphore: asyncio.Semaphore
    ) -> Optional[SemanticDuplicateResult]:
        """Analyze a single pair of code fragments."""
        async with semaphore:
            try:
                start_time = asyncio.get_event_loop().time()
                
                similarity = await self._intent_unified_facade.analyze_semantic_similarity(
                    code1, code2
                )
                
                analysis_time = asyncio.get_event_loop().time() - start_time
                
                return SemanticDuplicateResult(
                    code_record_1=candidate[0],
                    code_record_2=candidate[1],
                    semantic_similarity=similarity.similarity_score,
                    confidence=similarity.confidence,
                    analysis_method=similarity.method.value,
                    reasoning=similarity.reasoning,
                    analysis_time=analysis_time,
                    status=SemanticAnalysisStatus.SUCCESS,
                    metadata=similarity.metadata
                )
                
            except asyncio.TimeoutError:
                return SemanticDuplicateResult(
                    code_record_1=candidate[0],
                    code_record_2=candidate[1],
                    semantic_similarity=0.0,
                    confidence=0.0,
                    analysis_method="timeout",
                    reasoning="Analysis timed out",
                    analysis_time=0.0,
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
    
    def _normalize_code_indentation(self, code: str) -> str:
        """Normalize code indentation by removing common leading whitespace."""
        import textwrap
        
        # Remove common leading whitespace from all lines
        normalized = textwrap.dedent(code)
        
        # Also replace tabs with spaces
        normalized = normalized.expandtabs(4)
        
        return normalized.strip()