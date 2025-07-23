"""
Domain entity for code records.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any


@dataclass
class CodeRecord:
    """Domain entity representing a code record."""
    
    id: Optional[int] = None
    code_hash: Optional[str] = None
    code_content: Optional[str] = None
    normalized_code: Optional[str] = None
    function_name: Optional[str] = None
    file_path: Optional[str] = None
    timestamp: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None
    simhash: Optional[int] = None
    similarity_score: Optional[float] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.metadata is None:
            self.metadata = {}
    
    def generate_hash(self) -> str:
        """Generate SHA-256 hash for the code content."""
        import hashlib
        
        if self.normalized_code:
            content = self.normalized_code
        else:
            content = self.code_content or ""
        
        self.code_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
        return self.code_hash