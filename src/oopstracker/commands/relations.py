"""
Relations command implementation for OOPStracker CLI.
"""
from .base import BaseCommand


class RelationsCommand(BaseCommand):
    """Command to show relationships between code units."""
    
    async def execute(self) -> int:
        """Execute the relations command."""
        # Determine analysis mode
        use_fast_mode = self.args.fast and not self.args.full
        mode_name = "Fast SimHash" if use_fast_mode else "Full O(n²)"
        
        # Handle automatic threshold search
        if self.args.auto and not self.args.manual:
            return await self._execute_auto_mode(use_fast_mode, mode_name)
        
        # Specific hash analysis
        if self.args.hash:
            return await self._analyze_specific_hash(use_fast_mode, mode_name)
        
        # Interactive mode - show top connected units
        return await self._execute_interactive_mode(use_fast_mode, mode_name)
        
    async def _execute_auto_mode(self, use_fast_mode: bool, mode_name: str) -> int:
        """Execute auto threshold search mode."""
        print(f"🔄 Searching for optimal threshold ({mode_name} mode)...")
        print(f"   Target: ~{self.args.target} connections (max: {self.args.max_connections})")
        
        # Binary search for optimal threshold
        low_threshold = 0.1
        high_threshold = 0.9
        best_threshold = self.args.threshold
        best_connections = 0
        iterations = 0
        max_iterations = 10
        
        while iterations < max_iterations and high_threshold - low_threshold > 0.05:
            mid_threshold = (low_threshold + high_threshold) / 2
            iterations += 1
            
            print(f"\n   Iteration {iterations}: Testing threshold {mid_threshold:.3f}...")
            graph = self.detector.build_similarity_graph(mid_threshold, use_fast_mode)
            
            # Count total connections
            total_connections = sum(len(connections) for connections in graph.values())
            print(f"   Found {total_connections} connections")
            
            # Update best if closer to target
            if abs(total_connections - self.args.target) < abs(best_connections - self.args.target):
                best_threshold = mid_threshold
                best_connections = total_connections
            
            # Adjust search range
            if total_connections < self.args.target:
                high_threshold = mid_threshold
            elif total_connections > self.args.max_connections:
                low_threshold = mid_threshold
            else:
                # Close enough to target
                best_threshold = mid_threshold
                best_connections = total_connections
                break
        
        print(f"\n✅ Optimal threshold found: {best_threshold:.3f}")
        print(f"   Connections: {best_connections}")
        
        # Show results with optimal threshold
        self.args.threshold = best_threshold
        return await self._execute_interactive_mode(use_fast_mode, mode_name)
        
    async def _analyze_specific_hash(self, use_fast_mode: bool, mode_name: str) -> int:
        """Analyze relationships for a specific code hash."""
        # Clean up the hash if needed
        target_hash = self.args.hash.strip()
        
        # Find full hash if partial was provided
        full_hash = None
        for h in self.detector.records.keys():
            if h.startswith(target_hash):
                full_hash = h
                break
        
        if not full_hash:
            print(f"❌ Code hash not found: {target_hash}")
            print("   Use 'list' command to see available hashes")
            return 1
        
        record = self.detector.records.get(full_hash)
        if not record:
            print(f"❌ No record found for hash: {full_hash}")
            return 1
        
        # Show record info
        unit_type = record.metadata.get('type', 'unknown') if record.metadata else 'unknown'
        print(f"\n📝 Analyzing relations for:")
        print(f"   Type: {unit_type}")
        print(f"   Function: {record.function_name or 'N/A'}")
        print(f"   File: {record.file_path or 'N/A'}")
        print(f"   Hash: {record.code_hash}")
        
        # Find related units
        print(f"\n🔍 Finding related units ({mode_name} mode, threshold: {self.args.threshold})...")
        related = self.detector.find_related_units(
            full_hash,
            threshold=self.args.threshold,
            limit=self.args.limit,
            use_fast_mode=use_fast_mode
        )
        
        if not related:
            print(f"   No related units found with threshold {self.args.threshold}")
            print("   Try lowering the threshold with --threshold 0.2")
        else:
            print(f"   Found {len(related)} related units (threshold: {self.args.threshold}):\n")
            
            for i, (related_record, similarity) in enumerate(related, 1):
                unit_type = related_record.metadata.get('type', 'unknown') if related_record.metadata else 'unknown'
                func_name = related_record.function_name or 'N/A'
                file_path = related_record.file_path or 'N/A'
                
                # Get line information from CodeUnit if available
                unit = self.detector.code_units.get(related_record.code_hash)
                line_info = f":{unit.start_line}" if unit and unit.start_line else ""
                
                print(f"   {i:2d}. {unit_type}: {func_name} in {file_path}{line_info}")
                print(f"       Similarity: {similarity:.3f}")
                print(f"       Hash: {related_record.code_hash[:16]}...")
                print()
                
        return 0
        
    async def _execute_interactive_mode(self, use_fast_mode: bool, mode_name: str) -> int:
        """Execute interactive mode showing top connected units."""
        print(f"🔄 Building similarity graph ({mode_name} mode)...")
        graph = self.detector.build_similarity_graph(self.args.threshold, use_fast_mode)
        
        if not any(connections for connections in graph.values()):
            print(f"❌ No connections found with threshold {self.args.threshold}")
            print("   Try lowering the threshold with --threshold 0.2")
            return 0
        
        print(f"\n🕸️  Similarity Graph Overview (threshold: {self.args.threshold}):")
        
        # Show top connected units
        node_connections = [(hash_code, len(connections)) 
                          for hash_code, connections in graph.items() if connections]
        node_connections.sort(key=lambda x: x[1], reverse=True)
        
        print(f"   Top {min(10, len(node_connections))} most connected units:\n")
        
        for i, (hash_code, conn_count) in enumerate(node_connections[:10], 1):
            record = self.detector.records.get(hash_code)
            if record:
                unit_type = record.metadata.get('type', 'unknown') if record.metadata else 'unknown'
                func_name = record.function_name or 'N/A'
                file_path = record.file_path or 'N/A'
                
                # Get line information from CodeUnit if available
                unit = self.detector.code_units.get(hash_code)
                line_info = f":{unit.start_line}" if unit and unit.start_line else ""
                
                print(f"   {i:2d}. {unit_type}: {func_name} ({file_path}{line_info})")
                print(f"       {conn_count} connections | Hash: {record.code_hash[:16]}...")
                print()
        
        print(f"💡 Use --hash <code_hash> to see specific relations")
        print(f"💡 Use --graph to see full graph statistics")
        print(f"💡 Try different thresholds:")
        print(f"   0.8+ = Near duplicates")
        print(f"   0.6+ = Similar functions") 
        print(f"   0.4+ = Related patterns")
        print(f"   0.2+ = Loose similarities")
        
        return 0
        
    @classmethod
    def add_arguments(cls, parser):
        """Add command-specific arguments to the parser."""
        parser.add_argument(
            "--hash", 
            help="Code hash to find relations for (if not provided, shows overall graph stats)"
        )
        parser.add_argument(
            "--threshold", "-t",
            type=float,
            default=0.3,
            help="Similarity threshold for connections (default: 0.3)"
        )
        parser.add_argument(
            "--limit", "-l",
            type=int,
            default=10,
            help="Maximum number of related items to show (default: 10)"
        )
        parser.add_argument(
            "--graph",
            action="store_true",
            help="Show graph structure instead of specific relations"
        )
        parser.add_argument(
            "--fast",
            action="store_true",
            default=True,
            help="Use fast SimHash filtering (default: True)"
        )
        parser.add_argument(
            "--full",
            action="store_true",
            help="Use full O(n²) computation for maximum accuracy"
        )
        parser.add_argument(
            "--auto",
            action="store_true",
            default=True,
            help="Automatically find optimal threshold using adaptive search (default: True)"
        )
        parser.add_argument(
            "--manual",
            action="store_true",
            help="Use manual threshold instead of automatic search"
        )
        parser.add_argument(
            "--target",
            type=int,
            default=200,
            help="Target number of connections for auto mode (default: 200)"
        )
        parser.add_argument(
            "--max-connections",
            type=int,
            default=1000,
            help="Maximum connections before stopping in auto mode (default: 1000)"
        )