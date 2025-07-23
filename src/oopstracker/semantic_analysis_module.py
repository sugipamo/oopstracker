"""Semantic analysis module for code duplicate detection."""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Tuple, Any, Protocol
from dataclasses import dataclass
from enum import Enum

from .models import CodeRecord


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


class SemanticAnalyzerProtocol(Protocol):
    """Protocol for semantic analyzers."""
    
    async def analyze_semantic_similarity(
        self, code1: str, code2: str, language: str = "python"
    ) -> Dict[str, Any]:
        """Analyze semantic similarity between two code snippets."""
        ...


class SemanticAnalysisModule:
    """Module dedicated to semantic analysis of code duplicates."""
    
    def __init__(
        self, 
        semantic_analyzer: Optional[SemanticAnalyzerProtocol] = None,
        semantic_timeout: float = 30.0
    ):
        """Initialize semantic analysis module.
        
        Args:
            semantic_analyzer: Semantic analyzer implementation (dependency injection)
            semantic_timeout: Timeout for semantic analysis operations
        """
        self.logger = logging.getLogger(__name__)
        self._semantic_timeout = semantic_timeout
        self._semantic_analyzer = semantic_analyzer
        self.is_available = semantic_analyzer is not None
    
    async def analyze_semantic_duplicates(
        self,
        code_records: List[CodeRecord],
        structural_candidates: List[Tuple[CodeRecord, CodeRecord, float]],
        threshold: float = 0.7,
        max_concurrent: int = 3
    ) -> List[SemanticDuplicateResult]:
        """Analyze semantic similarity for structural duplicate candidates.
        
        Args:
            code_records: All code records
            structural_candidates: Candidates from structural analysis
            threshold: Minimum semantic similarity threshold
            max_concurrent: Maximum concurrent analyses
            
        Returns:
            List of semantic duplicate results
        """
        if not self.is_available or not self._semantic_analyzer:
            return []
        
        # Create batches for concurrent processing
        code_pairs = []
        for candidate in structural_candidates:
            if len(candidate) >= 2:
                code1, code2 = candidate[0], candidate[1]
                if code1.code_content and code2.code_content:
                    code_pairs.append((code1, code2, candidate))
        
        # Process in batches
        semantic_results = []
        
        # Semaphore for rate limiting
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def analyze_pair(code1: CodeRecord, code2: CodeRecord, candidate: Tuple) -> Optional[SemanticDuplicateResult]:
            """Analyze a single pair with rate limiting."""
            async with semaphore:
                try:
                    start_time = time.time()
                    
                    # Call semantic analysis with timeout
                    result = await asyncio.wait_for(
                        self._analyze_code_pair(code1, code2),
                        timeout=self._semantic_timeout
                    )
                    
                    analysis_time = time.time() - start_time
                    
                    return SemanticDuplicateResult(
                        code_record_1=code1,
                        code_record_2=code2,
                        semantic_similarity=result["similarity"],
                        confidence=result.get("confidence", 0.8),
                        analysis_method=result.get("method", "semantic_analyzer"),
                        reasoning=result.get("reasoning", ""),
                        analysis_time=analysis_time,
                        status=SemanticAnalysisStatus.SUCCESS,
                        metadata=result.get("metadata", {})
                    )
                    
                except asyncio.TimeoutError:
                    return SemanticDuplicateResult(
                        code_record_1=code1,
                        code_record_2=code2,
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
                        code_record_1=code1,
                        code_record_2=code2,
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
    
    async def _analyze_code_pair(self, code1: CodeRecord, code2: CodeRecord) -> Dict[str, Any]:
        """Analyze semantic similarity between two code records.
        
        Args:
            code1: First code record
            code2: Second code record
            
        Returns:
            Analysis result with similarity score and metadata
        """
        if not self._semantic_analyzer:
            raise Exception("Semantic analyzer not available")
        
        # Get language (default to Python)
        language = "python"
        
        # Analyze semantic similarity
        result = await self._semantic_analyzer.analyze_semantic_similarity(
            code1.code_content,
            code2.code_content,
            language=language
        )
        
        return {
            "similarity": result.get("semantic_similarity", 0.0),
            "confidence": result.get("confidence", 0.8),
            "method": "semantic_analyzer",
            "reasoning": result.get("reasoning", "Semantic analysis completed"),
            "metadata": {
                "intent_similarity": result.get("intent_similarity", 0.0),
                "structural_similarity": result.get("structural_similarity", 0.0),
                "features": result.get("features", {})
            }
        }
    
    async def quick_semantic_check(self, code1: str, code2: str, language: str = "python") -> Dict[str, Any]:
        """Quick semantic similarity check for two code fragments.
        
        Args:
            code1: First code fragment
            code2: Second code fragment
            language: Programming language
            
        Returns:
            Similarity analysis result
        """
        if not self.is_available or not self._semantic_analyzer:
            return {
                "available": False,
                "reason": "Semantic analysis not available"
            }
        
        try:
            result = await self._semantic_analyzer.analyze_semantic_similarity(
                code1, code2, language=language
            )
            
            return {
                "available": True,
                "similarity": result.get("semantic_similarity", 0.0),
                "confidence": result.get("confidence", 0.8),
                "reasoning": result.get("reasoning", ""),
                "metadata": result.get("metadata", {})
            }
        except Exception as e:
            self.logger.error(f"Quick semantic check failed: {e}")
            return {
                "available": False,
                "error": str(e)
            }