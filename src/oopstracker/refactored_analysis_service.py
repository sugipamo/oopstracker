"""
Refactored analysis service without try-catch complexity.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path

from .code_record import CodeRecord
from .unified_detector import UnifiedDetectionService, DetectionConfiguration
from .unified_repository import UnifiedRepository, OperationResult


@dataclass
class AnalysisResult:
    """Result of code analysis operation."""
    success: bool
    total_files: int = 0
    processed_records: int = 0
    duplicates_found: int = 0
    classifications: Dict[str, int] = None
    error_message: str = ""
    
    def __post_init__(self):
        if self.classifications is None:
            self.classifications = {}


class RefactoredAnalysisService:
    """
    Analysis service without try-catch complexity.
    Uses Result pattern for error handling.
    """
    
    def __init__(self, repository: UnifiedRepository, detector: UnifiedDetectionService):
        self.repository = repository
        self.detector = detector
        self.analysis_cache = {}
    
    def analyze_files(self, file_paths: List[str], detection_algorithm: str = "simhash") -> AnalysisResult:
        """Analyze files without try-catch blocks."""
        if not file_paths:
            return AnalysisResult(False, error_message="No files provided")
        
        # Get existing records
        records_result = self.repository.get_all_code_records()
        if not records_result.success:
            return AnalysisResult(False, error_message=f"Database error: {records_result.error_message}")
        
        existing_records = [self._dict_to_record(r) for r in records_result.data or []]
        
        # Process new files
        new_records = self._process_files(file_paths, existing_records)
        if not new_records:
            return AnalysisResult(False, error_message="No valid code records found in files")
        
        # Store new records
        storage_result = self._store_records(new_records)
        if not storage_result.success:
            return AnalysisResult(False, error_message=f"Storage error: {storage_result.error_message}")
        
        # Detect duplicates
        all_records = existing_records + new_records
        config = DetectionConfiguration(algorithm=detection_algorithm)
        duplicates = self.detector.detect_duplicates(all_records, detection_algorithm, config)
        
        # Generate classifications
        classifications = self._generate_classifications(all_records)
        
        return AnalysisResult(
            success=True,
            total_files=len(file_paths),
            processed_records=len(new_records),
            duplicates_found=len(duplicates),
            classifications=classifications
        )
    
    def find_similar_code(self, source_code: str, algorithm: str = "simhash") -> AnalysisResult:
        """Find similar code without try-catch."""
        if not source_code.strip():
            return AnalysisResult(False, error_message="Empty source code provided")
        
        # Get all records for comparison
        records_result = self.repository.get_all_code_records()
        if not records_result.success:
            return AnalysisResult(False, error_message=f"Database error: {records_result.error_message}")
        
        records = [self._dict_to_record(r) for r in records_result.data or []]
        
        # Find similar code
        config = DetectionConfiguration(algorithm=algorithm)
        similarity_result = self.detector.find_similar(source_code, records, algorithm, config)
        
        return AnalysisResult(
            success=True,
            processed_records=len(similarity_result.matched_records),
            duplicates_found=1 if similarity_result.is_duplicate else 0
        )
    
    def get_analysis_statistics(self) -> AnalysisResult:
        """Get analysis statistics without try-catch."""
        stats_result = self.repository.get_statistics()
        
        if not stats_result.success:
            return AnalysisResult(False, error_message=f"Statistics error: {stats_result.error_message}")
        
        stats = stats_result.data or {}
        
        return AnalysisResult(
            success=True,
            total_files=stats.get('total_files', 0),
            processed_records=stats.get('total_records', 0),
            classifications={
                'total_functions': stats.get('total_functions', 0)
            }
        )
    
    def _process_files(self, file_paths: List[str], existing_records: List[CodeRecord]) -> List[CodeRecord]:
        """Process files and extract code records."""
        new_records = []
        existing_hashes = {r.code_hash for r in existing_records if r.code_hash}
        
        for file_path in file_paths:
            file_records = self._extract_records_from_file(file_path, existing_hashes)
            new_records.extend(file_records)
        
        return new_records
    
    def _extract_records_from_file(self, file_path: str, existing_hashes: set) -> List[CodeRecord]:
        """Extract code records from a single file."""
        path = Path(file_path)
        
        if not path.exists() or not path.suffix == '.py':
            return []
        
        content = path.read_text(encoding='utf-8', errors='ignore')
        if not content.strip():
            return []
        
        # Simple function extraction (basic implementation)
        lines = content.split('\n')
        records = []
        
        for i, line in enumerate(lines):
            if line.strip().startswith('def '):
                function_name = line.split('def ')[1].split('(')[0].strip()
                
                # Get function body (simplified)
                function_lines = [line]
                for j in range(i + 1, len(lines)):
                    if lines[j].strip() and not lines[j].startswith(' ') and not lines[j].startswith('\t'):
                        break
                    function_lines.append(lines[j])
                
                function_code = '\n'.join(function_lines)
                code_hash = self._generate_hash(function_code)
                
                if code_hash not in existing_hashes:
                    record = CodeRecord(
                        code_hash=code_hash,
                        code_content=function_code,
                        normalized_code=self._normalize_code(function_code),
                        function_name=function_name,
                        file_path=str(path),
                        metadata={'type': 'function', 'line_number': i + 1}
                    )
                    records.append(record)
        
        return records
    
    def _store_records(self, records: List[CodeRecord]) -> OperationResult:
        """Store multiple records."""
        if not records:
            return OperationResult(True, affected_rows=0)
        
        records_data = [self._record_to_dict(r) for r in records]
        return self.repository.bulk_insert_records(records_data)
    
    def _generate_classifications(self, records: List[CodeRecord]) -> Dict[str, int]:
        """Generate classification statistics."""
        classifications = {}
        
        for record in records:
            record_type = record.metadata.get('type', 'unknown') if record.metadata else 'unknown'
            classifications[record_type] = classifications.get(record_type, 0) + 1
        
        return classifications
    
    def _dict_to_record(self, data: Dict[str, Any]) -> CodeRecord:
        """Convert dictionary to CodeRecord."""
        return CodeRecord(
            id=data.get('id'),
            code_hash=data.get('code_hash'),
            code_content=data.get('code_content'),
            normalized_code=data.get('normalized_code'),
            function_name=data.get('function_name'),
            file_path=data.get('file_path'),
            metadata=data.get('metadata', {}),
            simhash=data.get('simhash')
        )
    
    def _record_to_dict(self, record: CodeRecord) -> Dict[str, Any]:
        """Convert CodeRecord to dictionary."""
        return {
            'code_hash': record.code_hash,
            'code_content': record.code_content,
            'normalized_code': record.normalized_code,
            'function_name': record.function_name,
            'file_path': record.file_path,
            'timestamp': record.timestamp,
            'metadata': record.metadata or {},
            'simhash': record.simhash
        }
    
    def _generate_hash(self, code: str) -> str:
        """Generate hash for code content."""
        import hashlib
        return hashlib.sha256(code.encode('utf-8')).hexdigest()
    
    def _normalize_code(self, code: str) -> str:
        """Normalize code for comparison."""
        return code.lower().replace(' ', '').replace('\n', '').replace('\t', '')