# Copyright (c) 2025 OOPStracker Project
# Licensed under the MIT License

"""意味的重複検出の実装"""

import asyncio
import logging
import re
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass

from oopstracker.models import CodeRecord
from pattern_intent import IntentGenerator

logger = logging.getLogger(__name__)


@dataclass
class SemanticDuplicateResult:
    """意味的重複検出の結果"""
    code1: CodeRecord
    code2: CodeRecord
    structural_similarity: float
    semantic_similarity: float
    explanation: str
    intent1: str
    intent2: str
    is_duplicate: bool


class SemanticDuplicateAnalyzer:
    """意味的な類似性に基づく重複検出アナライザー"""
    
    def __init__(self, intent_generator: IntentGenerator = None):
        """
        Args:
            intent_generator: 意図生成器。指定しない場合は新規作成
        """
        self.intent_generator = intent_generator or IntentGenerator()
        self.logger = logger
    
    async def analyze(
        self,
        code_records: List[CodeRecord],
        structural_candidates: List[Tuple[CodeRecord, CodeRecord, float]],
        threshold: float = 0.7,
        max_concurrent: int = 5,
        max_candidates: int = 20
    ) -> List[SemanticDuplicateResult]:
        """構造的候補から意味的重複を分析
        
        Args:
            code_records: 全コードレコード（参照用）
            structural_candidates: 構造的重複候補
            threshold: 意味的類似度の閾値
            max_concurrent: 最大同時実行数
            max_candidates: 分析する最大候補数
            
        Returns:
            意味的重複の結果リスト
        """
        # Convert structural candidates to code pairs
        code_pairs = self._prepare_code_pairs(structural_candidates, max_candidates)
        
        if not code_pairs:
            return []
        
        # Perform semantic analysis
        semaphore = asyncio.Semaphore(max_concurrent)
        tasks = []
        
        for code1, code2, candidate in code_pairs:
            task = self._analyze_pair_with_semaphore(
                code1, code2, candidate, semaphore
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        # Filter out None results and sort by semantic similarity
        valid_results = [r for r in results if r is not None]
        valid_results.sort(key=lambda x: x.semantic_similarity, reverse=True)
        
        return valid_results
    
    def _prepare_code_pairs(
        self, 
        structural_candidates: List[Tuple[CodeRecord, CodeRecord, float]],
        max_candidates: int
    ) -> List[Tuple[str, str, Tuple[CodeRecord, CodeRecord, float]]]:
        """構造的候補をコードペアに変換
        
        Args:
            structural_candidates: 構造的重複候補
            max_candidates: 処理する最大候補数
            
        Returns:
            (code1, code2, candidate)のタプルのリスト
        """
        code_pairs = []
        for candidate in structural_candidates[:max_candidates]:
            try:
                # candidate is a tuple (CodeRecord, CodeRecord, float)
                code1 = self._normalize_code_indentation(candidate[0].code_content)
                code2 = self._normalize_code_indentation(candidate[1].code_content)
                code_pairs.append((code1, code2, candidate))
            except (AttributeError, IndexError):
                # Handle different candidate structures
                continue
        
        return code_pairs
    
    def _normalize_code_indentation(self, code: str) -> str:
        """コードのインデントを正規化"""
        lines = code.split('\n')
        # Remove empty lines at start/end
        while lines and not lines[0].strip():
            lines.pop(0)
        while lines and not lines[-1].strip():
            lines.pop()
        
        if not lines:
            return ""
        
        # Find minimum indentation
        min_indent = float('inf')
        for line in lines:
            if line.strip():
                indent = len(line) - len(line.lstrip())
                min_indent = min(min_indent, indent)
        
        # Normalize indentation
        if min_indent < float('inf'):
            normalized_lines = []
            for line in lines:
                if line.strip():
                    normalized_lines.append(line[min_indent:])
                else:
                    normalized_lines.append("")
            return '\n'.join(normalized_lines)
        
        return code
    
    async def _analyze_pair_with_semaphore(
        self,
        code1: str,
        code2: str,
        candidate: Tuple[CodeRecord, CodeRecord, float],
        semaphore: asyncio.Semaphore
    ) -> Optional[SemanticDuplicateResult]:
        """セマフォを使ってペアを分析"""
        async with semaphore:
            return await self._analyze_pair(code1, code2, candidate)
    
    async def _analyze_pair(
        self,
        code1: str,
        code2: str,
        candidate: Tuple[CodeRecord, CodeRecord, float]
    ) -> Optional[SemanticDuplicateResult]:
        """コードペアの意味的類似性を分析
        
        Args:
            code1: 正規化されたコード1
            code2: 正規化されたコード2
            candidate: 元の候補情報
            
        Returns:
            分析結果またはNone
        """
        try:
            # Generate intents for both codes
            intent1_result = await self.intent_generator.generate_intent(code1)
            intent2_result = await self.intent_generator.generate_intent(code2)
            
            intent1 = intent1_result.intent if intent1_result else "Unknown intent"
            intent2 = intent2_result.intent if intent2_result else "Unknown intent"
            
            # Calculate semantic similarity (simplified version)
            semantic_similarity = self._calculate_semantic_similarity(intent1, intent2)
            
            # Determine if duplicate
            is_duplicate = semantic_similarity >= 0.8
            
            # Generate explanation
            if is_duplicate:
                explanation = f"Both implement similar functionality: {intent1}"
            else:
                explanation = f"Different purposes: {intent1} vs {intent2}"
            
            return SemanticDuplicateResult(
                code1=candidate[0],
                code2=candidate[1],
                structural_similarity=candidate[2],
                semantic_similarity=semantic_similarity,
                explanation=explanation,
                intent1=intent1,
                intent2=intent2,
                is_duplicate=is_duplicate
            )
            
        except Exception as e:
            self.logger.error(f"Failed to analyze pair: {e}")
            return None
    
    def _calculate_semantic_similarity(self, intent1: str, intent2: str) -> float:
        """意図の意味的類似度を計算（簡易版）
        
        Args:
            intent1: 意図1
            intent2: 意図2
            
        Returns:
            類似度スコア (0.0-1.0)
        """
        # Simple word-based similarity
        words1 = set(re.findall(r'\w+', intent1.lower()))
        words2 = set(re.findall(r'\w+', intent2.lower()))
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1 & words2
        union = words1 | words2
        
        # Jaccard similarity
        similarity = len(intersection) / len(union) if union else 0.0
        
        # Boost similarity if key action words match
        action_words = {'create', 'update', 'delete', 'get', 'set', 'calculate', 
                       'compute', 'process', 'handle', 'manage', 'check', 'validate'}
        
        action1 = words1 & action_words
        action2 = words2 & action_words
        
        if action1 and action2 and action1 == action2:
            similarity = min(1.0, similarity + 0.3)
        
        return similarity