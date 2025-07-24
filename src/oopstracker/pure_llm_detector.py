"""
Pure LLM-based duplicate detector with no pattern matching or rule-based logic.
All decisions are made exclusively by LLM.
"""

import logging
from typing import List, Dict, Any
from datetime import datetime

from .code_record import CodeRecord
from .similarity_result import SimilarityResult
from .unified_detector import DuplicateDetector, DetectionConfiguration
from .llm_split_service import LLMSplitService


class PureLLMDetector(DuplicateDetector):
    """Pure LLM-based detector with no pattern matching."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.llm_service = LLMSplitService()
    
    def detect_duplicates(self, records: List[CodeRecord], config: DetectionConfiguration) -> List[SimilarityResult]:
        """Detect duplicates using pure LLM analysis."""
        if len(records) < 2:
            return []
        
        self.logger.info(f"Starting pure LLM duplicate detection for {len(records)} records")
        
        # Convert records to function format
        functions = self._convert_records_to_functions(records)
        if len(functions) < 2:
            return []
        
        # Rate limit protection: skip LLM analysis for large function sets
        max_functions_for_llm = 20  # Limit to prevent rate limit overload
        if len(functions) > max_functions_for_llm:
            self.logger.warning(f"Skipping LLM analysis for {len(functions)} functions (limit: {max_functions_for_llm}). Use smaller batches.")
            return []
        
        # Use synchronous LLM analysis - let errors propagate immediately
        duplicates = self._analyze_with_llm_sync(functions, config)
        
        self.logger.info(f"Pure LLM analysis completed, found {len(duplicates)} duplicate pairs")
        return duplicates
    
    def _convert_records_to_functions(self, records: List[CodeRecord]) -> List[Dict]:
        """Convert CodeRecord objects to function dictionaries."""
        functions = []
        for record in records:
            if record.code_content and record.function_name:
                functions.append({
                    'name': record.function_name,
                    'code': record.code_content,
                    'file_path': record.file_path or 'unknown',
                    '_record': record
                })
        return functions
    
    def _analyze_with_llm_sync(self, functions: List[Dict], config: DetectionConfiguration) -> List[SimilarityResult]:
        """Analyze functions using pure LLM - always use thread pool for safety."""
        import asyncio
        import concurrent.futures
        
        def run_async_analysis():
            return asyncio.run(self._analyze_with_llm_async(functions, config))
        
        # Always use thread pool executor to avoid async context conflicts
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(run_async_analysis)
            return future.result()
    
    async def _analyze_with_llm_async(self, functions: List[Dict], config: DetectionConfiguration) -> List[SimilarityResult]:
        """Pure LLM analysis - ask LLM to identify all duplicates."""
        # Prepare comprehensive prompt for LLM
        functions_text = self._format_functions_for_llm(functions)
        
        prompt = f"""
Analyze the following {len(functions)} Python functions and identify ALL semantically duplicate pairs.
Two functions are duplicates if they perform the same logical operation, regardless of:
- Variable names
- Minor implementation differences
- Comments or formatting

Functions to analyze:
{functions_text}

Respond with a JSON object containing:
{{
    "duplicate_pairs": [
        {{
            "function1_name": "exact_function_name_1",
            "function2_name": "exact_function_name_2", 
            "similarity_score": 0.95,
            "reasoning": "Both functions calculate the sum of two numbers"
        }}
    ]
}}

Only include pairs that are truly semantically equivalent. Be precise with function names.
"""
        
        await self.llm_service._ensure_llm_provider()
        
        async with self.llm_service.llm_provider as provider:
            response = await provider.generate(prompt)
        
        # Parse LLM response
        result = self.llm_service._parse_llm_response(response.content)
        
        # Convert LLM response to SimilarityResult objects
        return self._convert_llm_response_to_results(result, functions, config)
    
    def _format_functions_for_llm(self, functions: List[Dict]) -> str:
        """Format functions for LLM analysis."""
        formatted = []
        for i, func in enumerate(functions, 1):
            formatted.append(f"{i}. Function: {func['name']}")
            formatted.append(f"   File: {func['file_path']}")
            formatted.append(f"   Code:")
            # Indent the code
            code_lines = func['code'].split('\n')
            for line in code_lines:
                formatted.append(f"   {line}")
            formatted.append("")  # Empty line between functions
        
        return '\n'.join(formatted)
    
    def _convert_llm_response_to_results(self, llm_result: Dict, functions: List[Dict], config: DetectionConfiguration) -> List[SimilarityResult]:
        """Convert LLM response to SimilarityResult objects."""
        results = []
        
        # Create function name to record mapping
        name_to_record = {func['name']: func['_record'] for func in functions}
        
        duplicate_pairs = llm_result.get('duplicate_pairs', [])
        
        for pair in duplicate_pairs:
            func1_name = pair.get('function1_name', '')
            func2_name = pair.get('function2_name', '')
            similarity_score = float(pair.get('similarity_score', 0.0))
            reasoning = pair.get('reasoning', 'LLM identified as duplicate')
            
            # Find the corresponding records
            record1 = name_to_record.get(func1_name)
            record2 = name_to_record.get(func2_name)
            
            if record1 and record2 and similarity_score >= config.threshold:
                result = SimilarityResult(
                    is_duplicate=True,
                    similarity_score=similarity_score,
                    matched_records=[record1, record2],
                    analysis_method="pure_llm",
                    threshold=config.threshold
                )
                result.add_metadata('llm_reasoning', reasoning)
                result.add_metadata('llm_analysis', 'pure')
                results.append(result)
        
        return results
    
    def find_similar(self, source_code: str, records: List[CodeRecord], config: DetectionConfiguration) -> SimilarityResult:
        """Find similar code using pure LLM analysis."""
        if not source_code.strip():
            return SimilarityResult(False, 0.0, [], "pure_llm", config.threshold)
        
        # Create a temporary record for the source code
        source_record = CodeRecord(
            code_content=source_code,
            function_name="query_function",
            file_path="<query>"
        )
        
        # Add source to records and detect duplicates
        all_records = [source_record] + records
        duplicates = self.detect_duplicates(all_records, config)
        
        # Filter results that involve the source record
        matched_records = []
        max_similarity = 0.0
        
        for dup in duplicates:
            if source_record in dup.matched_records:
                other_records = [r for r in dup.matched_records if r != source_record]
                matched_records.extend(other_records)
                max_similarity = max(max_similarity, dup.similarity_score)
        
        return SimilarityResult(
            is_duplicate=len(matched_records) > 0,
            similarity_score=max_similarity,
            matched_records=matched_records,
            analysis_method="pure_llm",
            threshold=config.threshold
        )
    
    def get_algorithm_name(self) -> str:
        return "pure_llm"