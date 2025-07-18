"""Semantic-aware duplicate detector with fallback to structural analysis."""

import asyncio
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

from .models import CodeRecord
from .ast_simhash_detector import ASTSimHashDetector


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


class SemanticAwareDuplicateDetector:
    """Duplicate detector with semantic analysis capability."""
    
    def __init__(self, intent_unified_available: bool = True):
        """Initialize semantic-aware detector.
        
        Args:
            intent_unified_available: Whether intent_unified service is available
        """
        self.intent_unified_available = intent_unified_available
        self.structural_detector = ASTSimHashDetector()
        self.logger = logging.getLogger(__name__)
        self._intent_unified_facade = None
        self._semantic_timeout = 30.0
        self._semantic_threshold = 0.7
        
    async def initialize(self) -> None:
        """Initialize semantic analysis components."""
        if self.intent_unified_available:
            try:
                # Dynamic import to avoid hard dependency
                import sys
                import os
                
                # Add intent_unified to Python path
                intent_unified_path = os.path.join(
                    os.path.dirname(__file__), 
                    "../../../intent/intent-unified/src"
                )
                if intent_unified_path not in sys.path:
                    sys.path.insert(0, intent_unified_path)
                
                from intent_unified.core.facade import IntentUnifiedFacade
                
                self._intent_unified_facade = IntentUnifiedFacade()
                await self._intent_unified_facade.__aenter__()
                
                self.logger.info("Semantic analysis initialized successfully")
            except Exception as e:
                self.logger.warning(f"Failed to initialize semantic analysis: {e}")
                self.intent_unified_available = False
                self._intent_unified_facade = None
        
        # Always initialize structural detector
        # ASTSimHashDetector doesn't require async initialization
    
    async def cleanup(self) -> None:
        """Cleanup resources."""
        if self._intent_unified_facade:
            try:
                await self._intent_unified_facade.__aexit__(None, None, None)
            except Exception as e:
                self.logger.error(f"Error during semantic analyzer cleanup: {e}")
        
        # ASTSimHashDetector doesn't require cleanup
    
    async def detect_duplicates(
        self, 
        code_records: List[CodeRecord], 
        enable_semantic: bool = True,
        semantic_threshold: float = 0.7,
        max_concurrent: int = 3
    ) -> Dict[str, Any]:
        """Detect duplicates with semantic analysis.
        
        Args:
            code_records: List of code records to analyze
            enable_semantic: Whether to use semantic analysis
            semantic_threshold: Threshold for semantic similarity
            max_concurrent: Maximum concurrent semantic analyses
            
        Returns:
            Comprehensive duplicate detection results
        """
        # Phase 1: Structural duplicate detection (always run)
        structural_results = await self._detect_structural_duplicates(code_records)
        
        # Phase 2: Semantic analysis (if enabled and available)
        semantic_results = []
        if enable_semantic and self.intent_unified_available and self._intent_unified_facade:
            semantic_results = await self._analyze_semantic_duplicates(
                code_records=code_records,
                structural_candidates=structural_results.get("high_confidence", []),
                threshold=semantic_threshold,
                max_concurrent=max_concurrent
            )
        
        # Phase 3: Combine results
        combined_results = self._combine_results(
            structural_results, semantic_results, code_records
        )
        
        return {
            "structural_duplicates": structural_results,
            "semantic_duplicates": semantic_results,
            "combined_analysis": combined_results,
            "summary": self._generate_summary(
                structural_results, semantic_results, len(code_records)
            )
        }
    
    async def _detect_structural_duplicates(
        self, 
        code_records: List[CodeRecord]
    ) -> Dict[str, Any]:
        """Detect duplicates using structural analysis."""
        try:
            # Register code records with structural detector
            for record in code_records:
                if record.code_content and record.function_name:
                    self.structural_detector.register_code(
                        record.code_content, 
                        record.function_name, 
                        record.file_path
                    )
            
            # Find potential duplicates
            duplicates = self.structural_detector.find_potential_duplicates(
                threshold=0.7, use_fast_mode=True
            )
            
            # Categorize by confidence  
            high_confidence = []
            medium_confidence = []
            low_confidence = []
            
            for duplicate in duplicates:
                # duplicate is a tuple (CodeRecord, CodeRecord, float)
                if len(duplicate) >= 3:
                    similarity = duplicate[2]
                    if similarity >= 0.9:
                        high_confidence.append(duplicate)
                    elif similarity >= 0.7:
                        medium_confidence.append(duplicate)
                    else:
                        low_confidence.append(duplicate)
                else:
                    # Fallback categorization
                    medium_confidence.append(duplicate)
            
            return {
                "high_confidence": high_confidence,
                "medium_confidence": medium_confidence,
                "low_confidence": low_confidence,
                "total_found": len(duplicates)
            }
        except Exception as e:
            self.logger.error(f"Structural duplicate detection failed: {e}")
            return {
                "high_confidence": [],
                "medium_confidence": [],
                "low_confidence": [],
                "total_found": 0,
                "error": str(e)
            }
    
    async def _analyze_semantic_duplicates(
        self,
        code_records: List[CodeRecord],
        structural_candidates: List[Tuple[CodeRecord, CodeRecord, float]],
        threshold: float,
        max_concurrent: int
    ) -> List[SemanticDuplicateResult]:
        """Analyze semantic duplicates for structural candidates."""
        if not self._intent_unified_facade:
            return []
        
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
                    
                    similarity = await asyncio.wait_for(
                        self._intent_unified_facade.analyze_semantic_similarity(
                            code1, code2, timeout=self._semantic_timeout
                        ),
                        timeout=self._semantic_timeout + 5.0
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
    
    def _combine_results(
        self,
        structural_results: Dict[str, Any],
        semantic_results: List[SemanticDuplicateResult],
        code_records: List[CodeRecord]
    ) -> Dict[str, Any]:
        """Combine structural and semantic results."""
        
        # Create comprehensive duplicate groups
        duplicate_groups = []
        
        # Add high-confidence semantic duplicates
        for semantic_result in semantic_results:
            if semantic_result.status == SemanticAnalysisStatus.SUCCESS:
                duplicate_groups.append({
                    "type": "semantic",
                    "records": [semantic_result.code_record_1, semantic_result.code_record_2],
                    "similarity": semantic_result.semantic_similarity,
                    "confidence": semantic_result.confidence,
                    "method": semantic_result.analysis_method,
                    "reasoning": semantic_result.reasoning,
                    "analysis_time": semantic_result.analysis_time
                })
        
        # Add structural duplicates that weren't analyzed semantically
        for structural_duplicate in structural_results.get("high_confidence", []):
            # Check if this pair was already analyzed semantically
            # structural_duplicate is a tuple (CodeRecord, CodeRecord, float)
            already_analyzed = any(
                s.code_record_1 == structural_duplicate[0] and
                s.code_record_2 == structural_duplicate[1]
                for s in semantic_results
            )
            
            if not already_analyzed:
                duplicate_groups.append({
                    "type": "structural_only",
                    "records": [structural_duplicate[0], structural_duplicate[1]],
                    "similarity": structural_duplicate[2] if len(structural_duplicate) > 2 else 0.8,
                    "confidence": 0.7,  # Moderate confidence for structural only
                    "method": "structural_analysis",
                    "reasoning": "Structural similarity detected, semantic analysis not performed",
                    "analysis_time": 0.0
                })
        
        return {
            "duplicate_groups": duplicate_groups,
            "total_groups": len(duplicate_groups),
            "semantic_analyzed": len(semantic_results),
            "structural_only": len(structural_results.get("high_confidence", [])) - len(semantic_results)
        }
    
    def _generate_summary(self, structural_results: Dict[str, Any], semantic_results: List[SemanticDuplicateResult], total_records: int) -> Dict[str, Any]:
        """Generate summary of duplicate detection results."""
        
        successful_semantic = sum(1 for r in semantic_results if r.status == SemanticAnalysisStatus.SUCCESS)
        failed_semantic = len(semantic_results) - successful_semantic
        
        return {
            "total_code_records": total_records,
            "structural_duplicates_found": structural_results.get("total_found", 0),
            "semantic_analysis_attempted": len(semantic_results),
            "semantic_analysis_successful": successful_semantic,
            "semantic_analysis_failed": failed_semantic,
            "high_confidence_duplicates": len(structural_results.get("high_confidence", [])),
            "semantic_service_available": self.intent_unified_available,
            "recommendation": self._get_recommendation(structural_results, semantic_results)
        }
    
    def _get_recommendation(self, structural_results: Dict[str, Any], semantic_results: List[SemanticDuplicateResult]) -> str:
        """Get recommendation based on analysis results."""
        
        if not self.intent_unified_available:
            return "Semantic analysis unavailable - structural analysis only performed"
        
        successful_semantic = sum(1 for r in semantic_results if r.status == SemanticAnalysisStatus.SUCCESS)
        high_confidence_structural = len(structural_results.get("high_confidence", []))
        
        if successful_semantic == 0 and high_confidence_structural == 0:
            return "No duplicates detected"
        elif successful_semantic > 0:
            return f"Found {successful_semantic} semantic duplicates requiring attention"
        else:
            return f"Found {high_confidence_structural} structural duplicates - consider manual review"
    
    async def quick_semantic_check(self, code1: str, code2: str, language: str = "python") -> Dict[str, Any]:
        """Quick semantic similarity check for two code fragments."""
        
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
                code1, code2, language=language, timeout=self._semantic_timeout
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
    
    def _normalize_code_indentation(self, code: str) -> str:
        """Normalize code indentation by removing common leading whitespace."""
        import textwrap
        
        # Remove common leading whitespace from all lines
        normalized = textwrap.dedent(code)
        
        # Also replace tabs with spaces
        normalized = normalized.expandtabs(4)
        
        return normalized.strip()