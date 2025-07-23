# Copyright (c) 2025 OOPStracker Project
# Licensed under the MIT License

"""構造的重複検出の実装"""

import logging
from typing import List, Dict, Any, Tuple

from oopstracker.ast_simhash_detector import ASTSimHashDetector
from oopstracker.models import CodeRecord

logger = logging.getLogger(__name__)


class StructuralDuplicateAnalyzer:
    """構造的な類似性に基づく重複検出アナライザー"""
    
    def __init__(self, structural_detector: ASTSimHashDetector = None):
        """
        Args:
            structural_detector: 構造的重複検出器。指定しない場合は新規作成
        """
        self.structural_detector = structural_detector or ASTSimHashDetector()
        self.logger = logger
    
    async def analyze(
        self, 
        code_records: List[CodeRecord],
        threshold: float = 0.7,
        use_fast_mode: bool = True
    ) -> Dict[str, Any]:
        """構造的重複を検出
        
        Args:
            code_records: 分析対象のコードレコード
            threshold: 類似度の閾値
            use_fast_mode: 高速モードを使用するか
            
        Returns:
            信頼度別に分類された重複候補の辞書
        """
        try:
            # Register code records with structural detector
            for record in code_records:
                if record.code_content and record.function_name:
                    self.structural_detector.register_code(
                        record.code_content, 
                        record.function_name, 
                        record.file_path
                    )
            
            # Find potential duplicates (silent mode to avoid duplicate progress messages)
            duplicates = self.structural_detector.find_potential_duplicates(
                threshold=threshold, use_fast_mode=use_fast_mode, silent=True
            )
            
            # Categorize by confidence  
            categorized = self._categorize_by_confidence(duplicates)
            
            return categorized
        except Exception as e:
            self.logger.error(f"Structural duplicate detection failed: {e}")
            return {
                "high_confidence": [],
                "medium_confidence": [],
                "low_confidence": [],
                "total_found": 0,
                "error": str(e)
            }
    
    def _categorize_by_confidence(
        self, 
        duplicates: List[Tuple[CodeRecord, CodeRecord, float]]
    ) -> Dict[str, Any]:
        """重複候補を信頼度別に分類
        
        Args:
            duplicates: 重複候補のリスト
            
        Returns:
            信頼度別に分類された辞書
        """
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