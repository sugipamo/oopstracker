"""
Akinator command implementation for OOPStracker CLI.
"""
import sys
import re
from .base import BaseCommand


class AkinatorCommand(BaseCommand):
    """Command for interactive Akinator-style code exploration."""
    
    async def execute(self) -> int:
        """Execute the akinator command."""
        # Interactive Akinator-style code exploration
        if not self.semantic_detector:
            print("❌ Akinator mode requires semantic analysis")
            print("   Please ensure intent_tree is available")
            return 1
            
        print("🎯 Starting Akinator-style code exploration...")
        print("   This will ask you questions to find similar code")
        print()
        
        try:
            # Start exploration session
            exploration_result = await self.semantic_detector.explore_code_interactively(self.args.code)
            
            if not exploration_result.get("available", False):
                print(f"❌ Exploration not available: {exploration_result.get('reason', 'Unknown error')}")
                return 1
            
            session_id = exploration_result["session_id"]
            question_count = 0
            
            print(f"🔍 Exploring code (session: {session_id[:8]}...)")
            print(f"📝 Query code preview:")
            print(f"   {self.args.code[:100]}...")
            print()
            
            # Interactive question loop
            while question_count < self.args.max_questions:
                question = exploration_result.get("question")
                if not question:
                    print("✅ No more questions needed")
                    break
                
                question_count += 1
                print(f"❓ Question {question_count}/{self.args.max_questions}:")
                print(f"   {question['question_text']}")
                print(f"   Pattern: {question['pattern']}")
                print(f"   Expected impact: {question['expected_impact']:.3f}")
                print()
                
                # Get user answer or auto-answer
                if self.args.auto_answer:
                    # Auto-answer using regex matching
                    try:
                        pattern = re.compile(question['pattern'], re.MULTILINE | re.DOTALL)
                        matches = bool(pattern.search(self.args.code))
                        answer = "yes" if matches else "no"
                        print(f"🤖 Auto-answer: {answer}")
                    except re.error:
                        answer = "no"
                        print(f"🤖 Auto-answer: {answer} (invalid regex)")
                else:
                    # Interactive mode
                    while True:
                        try:
                            response = input("   Does this pattern match your code? (yes/no/quit): ").strip().lower()
                            if response in ['yes', 'y']:
                                answer = "yes"
                                break
                            elif response in ['no', 'n']:
                                answer = "no"
                                break
                            elif response in ['quit', 'q']:
                                print("🛑 Exploration cancelled")
                                return 0
                            else:
                                print("   Please answer 'yes', 'no', or 'quit'")
                        except KeyboardInterrupt:
                            print("\n🛑 Exploration cancelled")
                            return 0
                
                # Process answer
                matches = answer == "yes"
                result = await self.semantic_detector.answer_exploration_question(
                    session_id, question['feature_id'], matches
                )
                
                if not result.get("available", False):
                    print(f"❌ Failed to process answer: {result.get('reason', 'Unknown error')}")
                    break
                
                print(f"✅ Answer recorded: {answer}")
                
                if result["status"] == "completed":
                    print(f"🎉 Exploration completed!")
                    final_result = result.get("result")
                    if final_result:
                        if final_result["type"] == "existing":
                            snippet = final_result["snippet"]
                            print(f"📋 Found matching code:")
                            print(f"   Function: {snippet.get('function_name', 'N/A')}")
                            print(f"   File: {snippet.get('file_path', 'N/A')}")
                            print(f"   Hash: {snippet.get('code_hash', 'N/A')[:16]}...")
                            if snippet.get('code_content'):
                                print(f"   Code preview: {snippet['code_content'][:200]}...")
                        else:
                            print(f"💡 No existing code found - your code appears to be unique!")
                    break
                else:
                    candidates = result.get("candidates", [])
                    print(f"🔍 {len(candidates)} candidates remaining")
                    exploration_result = result  # Update for next iteration
                    print()
            
            if question_count >= self.args.max_questions:
                print(f"⏰ Reached maximum questions ({self.args.max_questions})")
                print("   Consider increasing --max-questions for more thorough exploration")
            
            # Show learning statistics if requested
            if self.args.show_learning:
                await self._show_learning_statistics()
                
        except Exception as e:
            print(f"❌ Akinator exploration failed: {e}")
            if self.args.log_level == "DEBUG":
                import traceback
                traceback.print_exc()
            return 1
            
        return 0
        
    async def _show_learning_statistics(self):
        """Show learning statistics from the exploration."""
        print(f"\n📊 Learning Statistics:")
        try:
            stats = await self.semantic_detector.get_learning_statistics()
            if stats.get("available", False):
                print(f"   Total features: {stats.get('total_features', 0)}")
                print(f"   Total usage: {stats.get('total_usage', 0)}")
                print(f"   Average information gain: {stats.get('avg_information_gain', 0):.3f}")
                
                most_used = stats.get('most_used_features', [])
                if most_used:
                    print(f"   Most used features:")
                    for i, feature in enumerate(most_used[:3], 1):
                        print(f"     {i}. {feature['description']}: {feature['match_count']} uses (gain: {feature['information_gain']:.3f})")
                
                most_effective = stats.get('most_effective_features', [])
                if most_effective:
                    print(f"   Most effective features:")
                    for i, feature in enumerate(most_effective[:3], 1):
                        print(f"     {i}. {feature['description']}: gain {feature['information_gain']:.3f} ({feature['match_count']} uses)")
                        
                # Show optimization potential
                optimization = await self.semantic_detector.optimize_features_from_history()
                if optimization.get("available", False):
                    print(f"   Optimization potential: {optimization.get('optimization_potential', False)}")
                    suggestions = optimization.get('new_feature_suggestions', [])
                    if suggestions:
                        print(f"   New feature suggestions:")
                        for i, suggestion in enumerate(suggestions[:2], 1):
                            print(f"     {i}. {suggestion['description']} (based on {suggestion['based_on']})")
            else:
                print(f"   Learning statistics not available: {stats.get('reason', 'Unknown')}")
        except Exception as e:
            print(f"   Failed to get learning statistics: {e}")
            
    @classmethod
    def add_arguments(cls, parser):
        """Add command-specific arguments to the parser."""
        parser.add_argument(
            "code",
            help="Code snippet to find similar code for"
        )
        parser.add_argument(
            "--max-questions",
            type=int,
            default=10,
            help="Maximum number of questions to ask (default: 10)"
        )
        parser.add_argument(
            "--timeout",
            type=int,
            default=30,
            help="Timeout for each question in seconds (default: 30)"
        )
        parser.add_argument(
            "--auto-answer",
            action="store_true",
            help="Auto-answer questions using regex matching (for testing)"
        )
        parser.add_argument(
            "--show-learning",
            action="store_true",
            help="Show learning statistics and feature effectiveness"
        )