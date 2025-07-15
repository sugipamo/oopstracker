"""
AST-based SimHash duplicate detection.
Uses structural analysis instead of text-based comparison.
"""

import logging
from typing import List, Dict, Optional, Tuple
from pathlib import Path

from .ast_analyzer import ASTAnalyzer, CodeUnit
from .models import CodeRecord, SimilarityResult
from .simhash_detector import BKTree
from .ast_database import ASTDatabaseManager


logger = logging.getLogger(__name__)


class ASTSimHashDetector:
    """
    AST-based SimHash detector for structural code similarity.
    """
    
    def __init__(self, hamming_threshold: int = 10, db_path: str = "oopstracker_ast.db"):
        """
        Initialize AST SimHash detector.
        
        Args:
            hamming_threshold: Maximum Hamming distance for similarity
            db_path: Path to SQLite database for persistence
        """
        self.hamming_threshold = hamming_threshold
        self.analyzer = ASTAnalyzer()
        self.bk_tree = BKTree()
        self.code_units: Dict[str, CodeUnit] = {}  # hash -> CodeUnit
        self.records: Dict[str, CodeRecord] = {}   # hash -> CodeRecord
        
        # Initialize database
        self.db_manager = ASTDatabaseManager(db_path)
        
        # Load existing data
        self._load_existing_data()
        
        logger.info(f"Initialized AST SimHash detector with threshold {hamming_threshold}, loaded {len(self.records)} existing records")
    
    def _load_existing_data(self):
        """
        Load existing data from database into memory structures.
        Only loads records from files that currently exist.
        """
        try:
            # First, get list of all files in the database
            existing_files = self.db_manager.get_existing_files()
            
            # Filter to only files that still exist
            valid_files = set()
            for file_path in existing_files:
                if Path(file_path).exists():
                    valid_files.add(file_path)
            
            logger.info(f"Found {len(valid_files)} existing files out of {len(existing_files)} tracked files")
            
            # Load all records
            existing_data = self.db_manager.get_all_records()
            loaded_count = 0
            skipped_count = 0
            
            for record, unit in existing_data:
                # Only load if file still exists
                if record.file_path and record.file_path in valid_files:
                    # Store in memory
                    self.records[record.code_hash] = record
                    self.code_units[record.code_hash] = unit
                    
                    # Rebuild BK-tree
                    if record.simhash is not None:
                        self.bk_tree.insert(record.simhash, record)
                    
                    loaded_count += 1
                else:
                    skipped_count += 1
            
            logger.info(f"Loaded {loaded_count} records from existing files, skipped {skipped_count} from deleted files")
            
        except Exception as e:
            logger.error(f"Failed to load existing data: {e}")
    
    def register_file(self, file_path: str, force: bool = False) -> List[CodeRecord]:
        """
        Register all code units from a file.
        
        Args:
            file_path: Path to Python file
            force: Force re-registration even if file hasn't changed
            
        Returns:
            List of registered CodeRecord objects
        """
        import hashlib
        
        logger.info(f"Registering file: {file_path}")
        
        # Check if file has changed
        if not force:
            try:
                with open(file_path, 'rb') as f:
                    current_hash = hashlib.sha256(f.read()).hexdigest()
                
                stored_hash = self.db_manager.get_file_hash(file_path)
                
                if stored_hash == current_hash:
                    logger.info(f"File {file_path} hasn't changed, skipping")
                    return []
            except Exception as e:
                logger.warning(f"Error checking file hash: {e}, proceeding with registration")
        
        # If file has changed, remove old records
        if self.db_manager.get_file_hash(file_path) is not None:
            logger.info(f"File {file_path} has changed, removing old records")
            removed = self.db_manager.remove_file_records(file_path)
            logger.info(f"Removed {removed} old records")
            
            # Also remove from memory structures
            records_to_remove = [r for r in self.records.values() if r.file_path == file_path]
            for record in records_to_remove:
                self.records.pop(record.code_hash, None)
                self.code_units.pop(record.code_hash, None)
        
        # Parse file into code units
        units = self.analyzer.parse_file(file_path)
        registered_records = []
        
        for unit in units:
            record = self._register_unit(unit)
            if record:
                registered_records.append(record)
        
        # Update file tracking
        if registered_records:
            with open(file_path, 'rb') as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()
            self.db_manager.update_file_tracking(file_path, file_hash, len(registered_records))
        
        logger.info(f"Registered {len(registered_records)} code units from {file_path}")
        return registered_records
    
    def register_code(self, source_code: str, function_name: Optional[str] = None,
                     file_path: Optional[str] = None) -> List[CodeRecord]:
        """
        Register code units from source code.
        
        Args:
            source_code: Python source code
            function_name: Optional function name hint
            file_path: Optional file path for context
            
        Returns:
            List of registered CodeRecord objects
        """
        logger.info("Registering code snippet")
        
        # Parse code into units
        units = self.analyzer.parse_code(source_code, file_path)
        registered_records = []
        
        for unit in units:
            # If function_name is provided, only register matching unit
            if function_name and unit.name != function_name:
                continue
            
            record = self._register_unit(unit)
            if record:
                registered_records.append(record)
        
        logger.info(f"Registered {len(registered_records)} code units")
        return registered_records
    
    def _register_unit(self, unit: CodeUnit) -> Optional[CodeRecord]:
        """
        Register a single code unit.
        
        Args:
            unit: Code unit to register
            
        Returns:
            CodeRecord if successfully registered, None otherwise
        """
        try:
            # Generate AST-based SimHash
            simhash = self.analyzer.generate_ast_simhash(unit)
            
            # Create CodeRecord
            record = CodeRecord(
                code_content=unit.source_code,
                function_name=unit.name if unit.type != "module" else None,
                file_path=unit.file_path,
                simhash=simhash,
                metadata={
                    "type": unit.type,
                    "start_line": unit.start_line,
                    "end_line": unit.end_line,
                    "complexity": unit.complexity_score,
                    "dependencies": unit.dependencies,
                    "ast_structure": unit.ast_structure
                }
            )
            
            # Generate hash and store
            record.generate_hash()
            
            # Store in database
            if self.db_manager.insert_record(record, unit):
                # Store in memory structures
                self.bk_tree.insert(simhash, record)
                self.code_units[record.code_hash] = unit
                self.records[record.code_hash] = record
                
                logger.debug(f"Registered {unit.type} '{unit.name}' with hash {record.code_hash[:16]}...")
                return record
            else:
                logger.debug(f"Record already exists: {unit.name}")
                return None
            
        except Exception as e:
            logger.error(f"Error registering unit {unit.name}: {e}")
            return None
    
    def find_similar(self, source_code: str, function_name: Optional[str] = None,
                    file_path: Optional[str] = None) -> SimilarityResult:
        """
        Find similar code units based on AST structure.
        
        Args:
            source_code: Python source code to check
            function_name: Optional function name hint
            file_path: Optional file path for context
            
        Returns:
            SimilarityResult with matching records
        """
        logger.info("Searching for similar code units")
        
        # Parse input code
        units = self.analyzer.parse_code(source_code, file_path)
        
        if not units:
            return SimilarityResult(
                is_duplicate=False,
                similarity_score=0.0,
                matched_records=[],
                analysis_method="ast_simhash"
            )
        
        # Use the first unit or find matching function
        target_unit = units[0]
        if function_name:
            for unit in units:
                if unit.name == function_name:
                    target_unit = unit
                    break
        
        return self._find_similar_unit(target_unit)
    
    def _find_similar_unit(self, target_unit: CodeUnit) -> SimilarityResult:
        """
        Find similar units for a given code unit.
        
        Args:
            target_unit: Code unit to find similarities for
            
        Returns:
            SimilarityResult with matching records
        """
        # Generate SimHash for target
        target_simhash = self.analyzer.generate_ast_simhash(target_unit)
        
        # Search in BK-tree
        similar_tuples = self.bk_tree.search(target_simhash, self.hamming_threshold)
        similar_records = [record for record, distance in similar_tuples]
        
        if not similar_records:
            logger.info("No similar code units found")
            return SimilarityResult(
                is_duplicate=False,
                similarity_score=0.0,
                matched_records=[],
                analysis_method="ast_simhash",
                threshold=self.hamming_threshold
            )
        
        # Calculate structural similarity scores
        scored_records = []
        for record in similar_records:
            stored_unit = self.code_units.get(record.code_hash)
            if stored_unit:
                structural_sim = self.analyzer.calculate_structural_similarity(
                    target_unit, stored_unit
                )
                record.similarity_score = structural_sim
                scored_records.append(record)
        
        # Sort by similarity score
        scored_records.sort(key=lambda r: r.similarity_score or 0, reverse=True)
        
        # Determine if duplicate
        is_duplicate = len(scored_records) > 0 and (scored_records[0].similarity_score or 0) > 0.7
        max_score = scored_records[0].similarity_score if scored_records else 0.0
        
        logger.info(f"Found {len(scored_records)} similar units, max similarity: {max_score:.3f}")
        
        return SimilarityResult(
            is_duplicate=is_duplicate,
            similarity_score=max_score or 0.0,
            matched_records=scored_records,
            analysis_method="ast_simhash",
            threshold=self.hamming_threshold
        )
    
    def analyze_code_structure(self, source_code: str, file_path: Optional[str] = None) -> Dict:
        """
        Analyze code structure without registering.
        
        Args:
            source_code: Python source code
            file_path: Optional file path for context
            
        Returns:
            Dictionary with analysis results
        """
        units = self.analyzer.parse_code(source_code, file_path)
        
        analysis = {
            "total_units": len(units),
            "functions": [u for u in units if u.type == "function"],
            "classes": [u for u in units if u.type == "class"]
        }
        
        # Add complexity analysis
        total_complexity = sum(u.complexity_score or 0 for u in units)
        analysis["total_complexity"] = total_complexity
        analysis["average_complexity"] = total_complexity / len(units) if units else 0
        
        # Add dependency analysis
        all_deps = set()
        for unit in units:
            all_deps.update(unit.dependencies or [])
        analysis["dependencies"] = sorted(all_deps)
        
        return analysis
    
    def get_statistics(self) -> Dict:
        """
        Get detector statistics.
        
        Returns:
            Dictionary with statistics
        """
        function_count = sum(1 for r in self.records.values() 
                           if r.metadata and r.metadata.get("type") == "function")
        class_count = sum(1 for r in self.records.values() 
                         if r.metadata and r.metadata.get("type") == "class")
        module_count = sum(1 for r in self.records.values() 
                          if r.metadata and r.metadata.get("type") == "module")
        
        try:
            # Get from database for accurate counts
            db_stats = self.db_manager.get_statistics()
            
            # Add detector-specific info
            db_stats["hamming_threshold"] = self.hamming_threshold
            db_stats["memory_loaded"] = len(self.records)
            
            return db_stats
        except Exception as e:
            logger.error(f"Failed to get database statistics: {e}")
            # Fallback to memory-based stats
            return {
                "total_units": len(self.records),
                "functions": function_count,
                "classes": class_count,
                "modules": module_count,
                "hamming_threshold": self.hamming_threshold,
                "memory_loaded": len(self.records)
            }
    
    def clear_memory(self):
        """Clear all stored data."""
        # Clear database
        self.db_manager.clear_all()
        
        # Clear memory structures
        self.bk_tree = BKTree()
        self.code_units.clear()
        self.records.clear()
        
        logger.info("Cleared AST SimHash detector memory and database")
    
    def get_all_records(self) -> List[CodeRecord]:
        """
        Get all registered records.
        
        Returns:
            List of all CodeRecord objects
        """
        return list(self.records.values())
    
    def find_potential_duplicates(self, threshold: float = 0.8) -> List[Tuple[CodeRecord, CodeRecord, float]]:
        """
        Find potential duplicate pairs across all registered code.
        
        Args:
            threshold: Minimum similarity threshold
            
        Returns:
            List of (record1, record2, similarity_score) tuples
        """
        logger.info(f"Searching for potential duplicates with threshold {threshold}")
        
        duplicates = []
        records = list(self.records.values())
        
        for i, record1 in enumerate(records):
            unit1 = self.code_units.get(record1.code_hash)
            if not unit1:
                continue
            
            for j, record2 in enumerate(records[i+1:], i+1):
                unit2 = self.code_units.get(record2.code_hash)
                if not unit2:
                    continue
                
                # Skip if same file and same type
                if (unit1.file_path == unit2.file_path and 
                    unit1.type == unit2.type and 
                    unit1.name == unit2.name):
                    continue
                
                similarity = self.analyzer.calculate_structural_similarity(unit1, unit2)
                
                if similarity >= threshold:
                    duplicates.append((record1, record2, similarity))
        
        # Sort by similarity score
        duplicates.sort(key=lambda x: x[2], reverse=True)
        
        logger.info(f"Found {len(duplicates)} potential duplicate pairs")
        return duplicates
    
    def build_similarity_graph(self, threshold: float = 0.3, use_fast_mode: bool = True) -> Dict[str, List[Tuple[str, float]]]:
        """
        Build a similarity graph showing relationships between all code units.
        
        Args:
            threshold: Minimum similarity threshold for connections
            use_fast_mode: Use SimHash filtering for faster computation
            
        Returns:
            Dictionary mapping code_hash to list of (connected_hash, similarity) tuples
        """
        if use_fast_mode:
            return self._build_similarity_graph_fast(threshold)
        else:
            return self._build_similarity_graph_full(threshold)
    
    def _build_similarity_graph_fast(self, threshold: float = 0.3) -> Dict[str, List[Tuple[str, float]]]:
        """
        Fast similarity graph using SimHash pre-filtering.
        Reduces computation from O(n²) to approximately O(n log n).
        """
        logger.info(f"Building similarity graph (FAST mode) with threshold {threshold}")
        
        graph = {}
        records = list(self.records.values())
        
        # Initialize graph nodes
        for record in records:
            graph[record.code_hash] = []
        
        # Convert structural similarity threshold to approximate Hamming distance
        # Empirical mapping: 0.3 similarity ≈ 15-20 Hamming distance
        hamming_threshold = max(5, int((1.0 - threshold) * 25))
        
        logger.debug(f"Using Hamming threshold {hamming_threshold} for similarity {threshold}")
        
        # Get SimHash-similar pairs from BK-tree
        simhash_pairs = self.bk_tree.find_all_pairs(hamming_threshold)
        
        logger.info(f"SimHash filtering found {len(simhash_pairs)} candidate pairs (vs {len(records)*(len(records)-1)//2} total)")
        
        # Calculate structural similarity only for SimHash candidates
        processed_pairs = 0
        for record1, record2, hamming_dist in simhash_pairs:
            unit1 = self.code_units.get(record1.code_hash)
            unit2 = self.code_units.get(record2.code_hash)
            
            if not unit1 or not unit2:
                continue
            
            # Skip if same file and same type
            if (unit1.file_path == unit2.file_path and 
                unit1.type == unit2.type and 
                unit1.name == unit2.name):
                continue
            
            # Calculate expensive structural similarity only for candidates
            similarity = self.analyzer.calculate_structural_similarity(unit1, unit2)
            processed_pairs += 1
            
            if similarity >= threshold:
                # Add bidirectional connection
                graph[record1.code_hash].append((record2.code_hash, similarity))
                graph[record2.code_hash].append((record1.code_hash, similarity))
        
        # Sort connections by similarity
        for code_hash in graph:
            graph[code_hash].sort(key=lambda x: x[1], reverse=True)
        
        connected_nodes = sum(1 for connections in graph.values() if connections)
        total_connections = sum(len(connections) for connections in graph.values()) // 2
        
        logger.info(f"Fast mode: processed {processed_pairs} pairs, found {total_connections} connections")
        logger.info(f"Performance: {processed_pairs}/{len(records)*(len(records)-1)//2} = {processed_pairs*100/(len(records)*(len(records)-1)//2 + 1):.1f}% of full computation")
        
        return graph
    
    def _build_similarity_graph_full(self, threshold: float = 0.3) -> Dict[str, List[Tuple[str, float]]]:
        """
        Full O(n²) similarity graph computation.
        Use only for small datasets or when maximum accuracy is needed.
        """
        logger.info(f"Building similarity graph (FULL mode) with threshold {threshold}")
        logger.warning("Full mode is O(n²) - may be slow for large datasets")
        
        graph = {}
        records = list(self.records.values())
        
        # Initialize graph nodes
        for record in records:
            graph[record.code_hash] = []
        
        # Build connections - O(n²)
        total_pairs = len(records) * (len(records) - 1) // 2
        processed = 0
        
        for i, record1 in enumerate(records):
            unit1 = self.code_units.get(record1.code_hash)
            if not unit1:
                continue
            
            for j, record2 in enumerate(records[i+1:], i+1):
                unit2 = self.code_units.get(record2.code_hash)
                if not unit2:
                    continue
                
                processed += 1
                if processed % 1000 == 0:
                    logger.info(f"Progress: {processed}/{total_pairs} pairs ({processed*100/total_pairs:.1f}%)")
                
                # Skip if same file and same type
                if (unit1.file_path == unit2.file_path and 
                    unit1.type == unit2.type and 
                    unit1.name == unit2.name):
                    continue
                
                similarity = self.analyzer.calculate_structural_similarity(unit1, unit2)
                
                if similarity >= threshold:
                    # Add bidirectional connection
                    graph[record1.code_hash].append((record2.code_hash, similarity))
                    graph[record2.code_hash].append((record1.code_hash, similarity))
        
        # Sort connections by similarity
        for code_hash in graph:
            graph[code_hash].sort(key=lambda x: x[1], reverse=True)
        
        connected_nodes = sum(1 for connections in graph.values() if connections)
        total_connections = sum(len(connections) for connections in graph.values()) // 2
        
        logger.info(f"Full mode: processed {processed} pairs, found {total_connections} connections")
        return graph
    
    def get_related_units(self, code_hash: str, threshold: float = 0.3, max_results: int = 10) -> List[Tuple[CodeRecord, float]]:
        """
        Get units related to a specific code unit.
        
        Args:
            code_hash: Hash of the target unit
            threshold: Minimum similarity threshold
            max_results: Maximum number of results to return
            
        Returns:
            List of (CodeRecord, similarity) tuples
        """
        target_unit = self.code_units.get(code_hash)
        if not target_unit:
            return []
        
        related = []
        
        for other_hash, other_record in self.records.items():
            if other_hash == code_hash:
                continue
            
            other_unit = self.code_units.get(other_hash)
            if not other_unit:
                continue
            
            similarity = self.analyzer.calculate_structural_similarity(target_unit, other_unit)
            
            if similarity >= threshold:
                related.append((other_record, similarity))
        
        # Sort by similarity and limit results
        related.sort(key=lambda x: x[1], reverse=True)
        return related[:max_results]
    
    def find_relations_adaptive(self, target_connections: int = 200, max_connections: int = 1000, 
                               min_threshold: float = 0.1, max_threshold: float = 0.95) -> Dict:
        """
        Adaptively find relations by adjusting threshold until target number of connections found.
        Uses random sampling to avoid performance bias and discover diverse relationships.
        
        Args:
            target_connections: Target number of connections to find
            max_connections: Maximum connections before stopping (quality threshold)
            min_threshold: Minimum similarity threshold to try
            max_threshold: Maximum similarity threshold to start from
            
        Returns:
            Dictionary with graph, metadata, and stopping criteria info
        """
        import random
        import time
        
        logger.info(f"Starting adaptive relation search (target: {target_connections}, max: {max_connections})")
        
        records = list(self.records.values())
        total_records = len(records)
        
        if total_records < 2:
            return {
                "graph": {},
                "threshold": max_threshold,
                "connections": 0,
                "stop_reason": "insufficient_data",
                "iterations": 0
            }
        
        # Adaptive search parameters
        threshold_step = 0.05
        current_threshold = max_threshold
        previous_connections = 0
        iteration = 0
        max_iterations = int((max_threshold - min_threshold) / threshold_step) + 1
        
        # Random sampling setup
        sample_size = min(1000, total_records)  # Sample for faster iteration
        
        results = {
            "iterations": [],
            "final_graph": {},
            "threshold": current_threshold,
            "connections": 0,
            "stop_reason": "max_iterations"
        }
        
        while current_threshold >= min_threshold and iteration < max_iterations:
            iteration += 1
            start_time = time.time()
            
            # Random sampling of records for this iteration
            sample_records = random.sample(records, sample_size) if total_records > sample_size else records
            
            logger.info(f"Iteration {iteration}: threshold={current_threshold:.2f}, sampling {len(sample_records)} records")
            
            # Build graph for sample with current threshold
            graph = self._build_sample_graph(sample_records, current_threshold)
            
            # Calculate statistics
            connected_nodes = sum(1 for connections in graph.values() if connections)
            total_connections = sum(len(connections) for connections in graph.values()) // 2
            
            # Scale up connection estimate to full dataset
            scale_factor = total_records / len(sample_records)
            estimated_full_connections = int(total_connections * scale_factor * scale_factor)
            
            iteration_time = time.time() - start_time
            
            # Record iteration results
            iteration_result = {
                "threshold": current_threshold,
                "sample_connections": total_connections,
                "estimated_connections": estimated_full_connections,
                "connected_nodes": connected_nodes,
                "sample_size": len(sample_records),
                "time": iteration_time
            }
            results["iterations"].append(iteration_result)
            
            logger.info(f"  Sample: {total_connections} connections, estimated full: {estimated_full_connections}")
            
            # Check stopping criteria
            stop_reason = None
            
            # 1. Target reached
            if target_connections <= estimated_full_connections <= max_connections:
                stop_reason = "target_reached"
                logger.info(f"Target reached: {estimated_full_connections} connections")
            
            # 2. Exceeded maximum
            elif estimated_full_connections > max_connections:
                # Use previous threshold
                if iteration > 1:
                    current_threshold += threshold_step
                    prev_result = results["iterations"][-2]
                    estimated_full_connections = prev_result["estimated_connections"]
                stop_reason = "max_exceeded"
                logger.info(f"Max exceeded, using previous threshold: {current_threshold:.2f}")
            
            # 3. Growth rate too high (quality drop)
            elif iteration > 1 and previous_connections > 0:
                growth_rate = estimated_full_connections / previous_connections
                if growth_rate > 3.0:
                    # Use previous threshold
                    current_threshold += threshold_step
                    prev_result = results["iterations"][-2]
                    estimated_full_connections = prev_result["estimated_connections"]
                    stop_reason = "growth_rate_exceeded"
                    logger.info(f"Growth rate too high ({growth_rate:.1f}x), using previous threshold")
            
            if stop_reason:
                # Build final graph with full dataset
                logger.info(f"Building final graph with full dataset (threshold: {current_threshold:.2f})")
                final_graph = self._build_similarity_graph_fast(current_threshold)
                
                results.update({
                    "final_graph": final_graph,
                    "threshold": current_threshold,
                    "connections": sum(len(connections) for connections in final_graph.values()) // 2,
                    "stop_reason": stop_reason
                })
                break
            
            previous_connections = estimated_full_connections
            current_threshold -= threshold_step
        
        logger.info(f"Adaptive search completed: {iteration} iterations, threshold: {results['threshold']:.2f}, "
                   f"connections: {results['connections']}, reason: {results['stop_reason']}")
        
        return results
    
    def _build_sample_graph(self, sample_records: List, threshold: float) -> Dict[str, List[Tuple[str, float]]]:
        """
        Build similarity graph for a sample of records.
        Used for adaptive threshold searching.
        """
        graph = {}
        
        # Initialize graph nodes
        for record in sample_records:
            graph[record.code_hash] = []
        
        # Convert threshold to hamming distance
        hamming_threshold = max(5, int((1.0 - threshold) * 25))
        
        # Get SimHash pairs for sample
        sample_hashes = {record.code_hash for record in sample_records}
        
        # Build connections efficiently
        for i, record1 in enumerate(sample_records):
            unit1 = self.code_units.get(record1.code_hash)
            if not unit1:
                continue
            
            # Find similar records using BK-tree
            similar_results = self.bk_tree.search(record1.simhash, hamming_threshold)
            
            for similar_record, hamming_dist in similar_results:
                # Only include if in sample
                if similar_record.code_hash not in sample_hashes:
                    continue
                
                if similar_record.code_hash == record1.code_hash:
                    continue
                
                unit2 = self.code_units.get(similar_record.code_hash)
                if not unit2:
                    continue
                
                # Skip if same file and same type
                if (unit1.file_path == unit2.file_path and 
                    unit1.type == unit2.type and 
                    unit1.name == unit2.name):
                    continue
                
                # Calculate structural similarity
                similarity = self.analyzer.calculate_structural_similarity(unit1, unit2)
                
                if similarity >= threshold:
                    # Add unidirectional connection (will be made bidirectional later)
                    if similar_record.code_hash not in [conn[0] for conn in graph[record1.code_hash]]:
                        graph[record1.code_hash].append((similar_record.code_hash, similarity))
                        graph[similar_record.code_hash].append((record1.code_hash, similarity))
        
        return graph