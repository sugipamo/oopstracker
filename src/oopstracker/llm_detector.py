"""
LLM-based duplicate detector that requires LLM for all operations.
"""

import asyncio
import logging
from typing import List, Dict, Any
from datetime import datetime

from .code_record import CodeRecord
from .similarity_result import SimilarityResult
from .unified_detector import DuplicateDetector, DetectionConfiguration
from .llm_split_service import LLMSplitService
from .function_group_clustering import FunctionGroup


class LLMDuplicateDetector(DuplicateDetector):
    """LLM-based duplicate detector that uses semantic analysis."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.llm_service = LLMSplitService()
    
    def detect_duplicates(self, records: List[CodeRecord], config: DetectionConfiguration) -> List[SimilarityResult]:
        """Detect duplicates using LLM semantic analysis."""
        if len(records) < 2:
            return []
        
        self.logger.info(f"Starting LLM-based duplicate detection for {len(records)} records")
        
        # Convert records to function format for LLM
        functions = []
        for record in records:
            if record.code_content and record.function_name:
                functions.append({
                    'name': record.function_name,
                    'code': record.code_content,
                    'file_path': record.file_path,
                    'record': record
                })
        
        if len(functions) < 2:
            return []
        
        # Use asyncio to run the LLM analysis
        try:
            # Check if we're already in an async context
            try:
                loop = asyncio.get_running_loop()
                # We're in an async context, create a task
                import concurrent.futures
                
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, self._analyze_duplicates_with_llm(functions, config))
                    results = future.result()
            except RuntimeError:
                # No running loop, we can use asyncio.run
                results = asyncio.run(self._analyze_duplicates_with_llm(functions, config))
            
            self.logger.info(f"LLM analysis completed, found {len(results)} duplicate pairs")
            return results
        except Exception as e:
            self.logger.error(f"LLM duplicate detection failed: {e}")
            raise RuntimeError(f"LLM is required but failed: {e}")
    
    async def _analyze_duplicates_with_llm(self, functions: List[Dict], config: DetectionConfiguration) -> List[SimilarityResult]:
        """Analyze functions for duplicates using LLM."""
        results = []
        
        # Group functions for analysis
        groups = self._create_analysis_groups(functions)
        
        for group in groups:
            if len(group) >= 2:
                # Use LLM to analyze semantic similarity within each group
                group_results = await self._analyze_group_similarities(group, config)
                results.extend(group_results)
        
        return results
    
    def _create_analysis_groups(self, functions: List[Dict]) -> List[List[Dict]]:
        """Create groups of functions for analysis based on names and patterns."""
        # Simple grouping by function name patterns
        from collections import defaultdict
        
        groups_dict = defaultdict(list)
        
        for func in functions:
            name = func['name']
            # Group by common prefixes (get_, set_, validate_, etc.)
            if '_' in name:
                prefix = name.split('_')[0]
                groups_dict[f"prefix_{prefix}"].append(func)
            else:
                # Group short functions together
                if len(name) < 10:
                    groups_dict["short_names"].append(func)
                else:
                    groups_dict["long_names"].append(func)
        
        # Also create a general group for cross-pattern analysis
        if len(functions) <= 20:  # Only for small sets
            groups_dict["all_functions"] = functions
        
        return [group for group in groups_dict.values() if len(group) >= 2]
    
    async def _analyze_group_similarities(self, group: List[Dict], config: DetectionConfiguration) -> List[SimilarityResult]:
        """Analyze similarities within a group using LLM."""
        results = []
        
        # Compare each pair in the group
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                func1, func2 = group[i], group[j]
                
                # Use LLM to determine semantic similarity
                is_similar, similarity_score, reasoning = await self._compare_functions_with_llm(func1, func2)
                
                if is_similar and similarity_score >= config.threshold:
                    result = SimilarityResult(
                        is_duplicate=True,
                        similarity_score=similarity_score,
                        matched_records=[func1['record'], func2['record']],
                        analysis_method="llm_semantic",
                        threshold=config.threshold
                    )
                    result.add_metadata('llm_reasoning', reasoning)
                    results.append(result)
        
        return results
    
    async def _compare_functions_with_llm(self, func1: Dict, func2: Dict) -> tuple[bool, float, str]:
        """Compare two functions using LLM."""
        prompt = f"""
Compare these two Python functions for semantic similarity. Consider their purpose, logic, and functionality rather than just syntax.

Function 1: {func1['name']}
```python
{func1['code']}
```

Function 2: {func2['name']}
```python
{func2['code']}
```

Respond with a JSON object containing:
- "similar": boolean (true if functions are semantically similar)
- "similarity_score": float between 0.0 and 1.0
- "reasoning": string explaining your analysis

Consider functions similar if they:
- Perform the same logical operation
- Have the same intended purpose
- Implement similar algorithms (even with different variable names)
"""
        
        try:
            await self.llm_service._ensure_llm_provider()
            
            async with self.llm_service.llm_provider as provider:
                response = await provider.generate(prompt)
            
            # Parse LLM response
            result = self.llm_service._parse_llm_response(response.content)
            
            is_similar = result.get('similar', False)
            similarity_score = float(result.get('similarity_score', 0.0))
            reasoning = result.get('reasoning', 'No reasoning provided')
            
            return is_similar, similarity_score, reasoning
            
        except Exception as e:
            self.logger.warning(f"LLM comparison failed for {func1['name']} vs {func2['name']}: {e}")
            return False, 0.0, f"LLM analysis failed: {e}"
    
    def find_similar(self, source_code: str, records: List[CodeRecord], config: DetectionConfiguration) -> SimilarityResult:
        """Find similar code using LLM analysis."""
        if not source_code.strip():
            return SimilarityResult(False, 0.0, [], "llm_semantic", config.threshold)
        
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
            analysis_method="llm_semantic",
            threshold=config.threshold
        )
    
    def get_algorithm_name(self) -> str:
        return "llm_semantic"