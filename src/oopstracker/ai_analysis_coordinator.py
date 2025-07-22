"""
AI Analysis Coordinator - Application layer component for AI analysis coordination.
Replaces the confusing "UnifiedLLMService" naming with proper layer terminology.
"""

import asyncio
import logging
import re
from typing import Dict, List, Optional, Any, Union, Tuple
from abc import ABC, abstractmethod
from datetime import datetime
from dataclasses import dataclass

# Import extracted modules
from .ai_analysis_models import AnalysisRequest, ClassificationRule, AnalysisResponse
from .classification_rule_repository import ClassificationRuleRepository
from .llm_extractor import LLMExtractor
from .classification_service import ClassificationService
from .intent_analysis_service import IntentAnalysisService
from .similarity_analysis_service import SimilarityAnalysisService

try:
    from intent_unified.core.semantic_analyzer import SemanticDuplicateAnalyzer, UnifiedConfig
    from llm_providers import create_provider, LLMConfig
    AI_AVAILABLE = True
except ImportError as e:
    AI_AVAILABLE = False


# Data models have been extracted to their respective modules


class AIAnalysisInterface(ABC):
    """Interface for AI analysis capabilities."""
    
    @abstractmethod
    async def analyze_similarity(self, code1: str, code2: str, **kwargs) -> AnalysisResponse:
        """Analyze semantic similarity between two code snippets."""
        pass
    
    @abstractmethod
    async def classify_function(self, code: str, categories: List[str], **kwargs) -> AnalysisResponse:
        """Classify a function into predefined categories."""
        pass
    
    @abstractmethod
    async def analyze_intent(self, code: str, **kwargs) -> AnalysisResponse:
        """Analyze the intent/purpose of code."""
        pass


class AIAnalysisCoordinator(AIAnalysisInterface):
    """
    Coordinates AI analysis requests across the application.
    
    This is an application layer component that orchestrates AI analysis
    without exposing low-level AI service details to the domain layer.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._semantic_analyzer = None
        self._llm_provider = None
        self._available = False
        self._initialized = False
        
        # Initialize rule-based classification
        self.rule_repository = ClassificationRuleRepository()
        
        # Initialize service components
        self._classification_service = None
        self._intent_service = None
        self._similarity_service = None
        
        if AI_AVAILABLE:
            self._init_available = True
        else:
            self._init_available = False
            self.logger.error("AI not available - LLM configuration required")
            raise RuntimeError("AI services are not available. Please install and configure LLM dependencies.")
    
    async def cleanup(self):
        """Clean up resources."""
        if self._llm_provider:
            await self._llm_provider.cleanup()
        if self._semantic_analyzer:
            await self._semantic_analyzer.cleanup()
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_initialized()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.cleanup()
    
    async def _ensure_initialized(self):
        """Ensure AI components are initialized."""
        if self._initialized or not self._init_available:
            return
            
        try:
            # Create config for semantic analyzer
            unified_config = UnifiedConfig.from_env()
            self._semantic_analyzer = SemanticDuplicateAnalyzer(unified_config)
            
            # Initialize LLM provider using PresetManager
            from llm_providers import PresetManager
            
            preset_manager = PresetManager()
            preset = preset_manager.get_default_preset()
            
            if not preset:
                raise RuntimeError("No LLM presets configured. Please use 'llm-providers presets add' to configure an LLM endpoint.")
            
            self.logger.info(f"Using preset '{preset.name}'")
            
            config = LLMConfig(
                provider=preset.provider_type,
                model=preset.model,
                base_url=preset.base_url,
                temperature=preset.temperature,
                max_tokens=preset.max_tokens,
                timeout=preset.timeout,
                retry_count=3,
                retry_delay=0.5
            )
            self._llm_provider = await create_provider(config)
            
            # Initialize service components
            self._classification_service = ClassificationService(self._llm_provider, self.rule_repository)
            self._intent_service = IntentAnalysisService(self._llm_provider)
            self._similarity_service = SimilarityAnalysisService(self._semantic_analyzer)
            
            self._available = True
            self._initialized = True
            self.logger.info(f"AI analysis coordinator initialized with LLM preset '{preset.name}' at {config.base_url}")
        except Exception as e:
            self.logger.warning(f"Failed to initialize AI analyzer: {e}")
            self._available = False
            self._initialized = True
    
    @property
    def available(self) -> bool:
        """Check if AI analysis is available."""
        # Return true if dependencies are available (will be initialized on first use)
        return self._init_available
    
    async def analyze_similarity(self, code1: str, code2: str, **kwargs) -> AnalysisResponse:
        """Coordinate similarity analysis between two code snippets."""
        await self._ensure_initialized()
        
        if not self._available or not self._similarity_service:
            raise RuntimeError("AI analysis is not available. Please configure LLM settings.")
        
        # Delegate to similarity service
        return await self._similarity_service.analyze_similarity(code1, code2, **kwargs)
    
    async def classify_function(self, code: str, categories: List[str], **kwargs) -> AnalysisResponse:
        """
        Coordinate function classification using rule-based approach with LLM fallback.
        
        Process:
        1. Try existing rules first (fast, no LLM call)
        2. If no rules match, generate new rule with LLM  
        3. Apply new rule and save for future use
        """
        await self._ensure_initialized()
        
        if not self._classification_service:
            raise RuntimeError("Classification service is not available.")
        
        # Delegate to classification service
        return await self._classification_service.classify_function(code, categories, **kwargs)
    
    async def generate_classification_pattern(self, sample_functions: List[Dict[str, Any]], **kwargs) -> AnalysisResponse:
        """Generate a regex pattern for splitting functions using LLM.
        
        Args:
            sample_functions: List of function dictionaries with 'name' and 'code' keys
            
        Returns:
            AnalysisResponse with classification pattern data
        """
        await self._ensure_initialized()
        
        if not self._classification_service:
            raise RuntimeError("Classification service is not available.")
        
        # Delegate to classification service
        return await self._classification_service.generate_classification_pattern(sample_functions, **kwargs)
    
    async def analyze_intent(self, code: str, **kwargs) -> AnalysisResponse:
        """Coordinate intent analysis of code."""
        start_time = asyncio.get_event_loop().time()
        
        await self._ensure_initialized()
        
        if not self._available:
            raise RuntimeError("AI analysis is not available. Please configure LLM settings.")
        
        try:
            intent_prompt = f"""Analyze the purpose and functionality of this code:

```python
{code}
```

REQUIRED RESPONSE FORMAT:
```analysis
purpose: <main purpose in 1-2 sentences>
functionality: <specific functionality description>
confidence: <confidence level 0.0-1.0>
```

EXAMPLE:
```analysis
purpose: Retrieve user information from database
functionality: Takes ID and executes SQL query to return user dictionary
confidence: 0.9
```

IMPORTANT:
- MUST use the exact markdown block format above
- No additional explanations outside the block
- Keep responses concise and structured"""
            
            # Use LLM provider for intent analysis
            llm_response = await self._llm_provider.generate(intent_prompt)
            response_text = llm_response.content if hasattr(llm_response, 'content') else str(llm_response)
            
            # Parse response flexibly (try Markdown block first, then fallback to text extraction)
            import re
            try:
                # Try Markdown block format first
                analysis_match = re.search(
                    r'```analysis\s*\n(.*?)\n```', 
                    response_text, 
                    re.DOTALL | re.IGNORECASE
                )
                
                if analysis_match:
                    block_content = analysis_match.group(1).strip()
                    
                    # Extract fields from block
                    purpose_match = re.search(r'purpose:\s*([^\n\r]+)', block_content, re.IGNORECASE)
                    functionality_match = re.search(r'functionality:\s*([^\n\r]+)', block_content, re.IGNORECASE)
                    confidence_match = re.search(r'confidence:\s*([^\n\r]+)', block_content, re.IGNORECASE)
                    
                    purpose = purpose_match.group(1).strip() if purpose_match else "General purpose function"
                    functionality = functionality_match.group(1).strip() if functionality_match else "General functionality"
                    confidence = float(confidence_match.group(1).strip()) if confidence_match else 0.7
                else:
                    # Fallback: extract from any text format or analyze content
                    purpose_match = re.search(r'purpose:\s*([^\n\r]+)', response_text, re.IGNORECASE)
                    functionality_match = re.search(r'functionality:\s*([^\n\r]+)', response_text, re.IGNORECASE)
                    
                    if purpose_match:
                        purpose = purpose_match.group(1).strip()
                        functionality = functionality_match.group(1).strip() if functionality_match else "General functionality"
                        confidence = 0.7
                    else:
                        # Fallback to default values
                        purpose = None
                        functionality = None
                        confidence = 0.3
                        if not purpose:
                            purpose = "Unknown purpose"
                            functionality = "General functionality"
                            confidence = 0.3
                    
            except (ValueError, AttributeError) as parse_error:
                self.logger.warning(f"Failed to parse LLM intent response: {parse_error}")
                purpose = "General purpose function"
                functionality = "General functionality"
                confidence = 0.3
            
            processing_time = asyncio.get_event_loop().time() - start_time
            
            return AnalysisResponse(
                success=True,
                result={
                    "purpose": purpose,
                    "functionality": functionality
                },
                confidence=confidence,
                reasoning="Intent analyzed using AI",
                metadata={
                    "analysis_method": "ai_intent_analysis"
                },
                processing_time=processing_time
            )
            
        except Exception as e:
            processing_time = asyncio.get_event_loop().time() - start_time
            self.logger.error(f"AI intent analysis failed: {e}")
            
            return AnalysisResponse(
                success=False,
                result={"purpose": "Unknown", "functionality": "Unknown"},
                confidence=0.0,
                reasoning=f"Intent analysis failed: {str(e)[:100]}",
                metadata={"error": str(e)},
                processing_time=processing_time
            )


# Singleton instance
_ai_coordinator = None

def get_ai_coordinator() -> AIAnalysisInterface:
    """Get singleton instance of AI coordinator."""
    global _ai_coordinator
    
    if _ai_coordinator is None:
        _ai_coordinator = AIAnalysisCoordinator()
    
    return _ai_coordinator


async def demo_ai_coordinator():
    """Demo the AI analysis coordinator."""
    print("🤖 AI Analysis Coordinator Demo")
    print("=" * 35)
    
    # Test with real coordinator
    coordinator = get_ai_coordinator()
    
    test_code = """
def process_user_data(user_data):
    if not user_data.get('email'):
        raise ValueError('Email required')
    return {'id': user_data['id'], 'email': user_data['email']}
"""
    
    # Test classification
    categories = ['getter', 'setter', 'business_logic', 'validation', 'constructor']
    classification = await coordinator.classify_function(test_code, categories)
    
    print(f"Classification: {classification.result}")
    print(f"Confidence: {classification.confidence:.2f}")
    print(f"Reasoning: {classification.reasoning}")
    
    # Test intent analysis
    intent = await coordinator.analyze_intent(test_code)
    
    print(f"\nIntent Analysis:")
    print(f"Purpose: {intent.result['purpose']}")
    print(f"Functionality: {intent.result['functionality']}")
    print(f"Confidence: {intent.confidence:.2f}")


if __name__ == "__main__":
    asyncio.run(demo_ai_coordinator())