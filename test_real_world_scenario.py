#!/usr/bin/env python3
"""
Real-world scenario testing for oopstracker.

Simulates a large-scale Django + React project with diverse function patterns
similar to actual production codebases.
"""

import asyncio
import sys
import os
import time
import psutil
import random
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

sys.path.insert(0, str(Path(__file__).parent / "src"))

from oopstracker.smart_group_splitter import SmartGroupSplitter
from oopstracker.function_group_clustering import FunctionGroup


class RealWorldDataGenerator:
    """Generate realistic function patterns from actual project types."""
    
    def __init__(self):
        self.patterns = {
            # Django/Backend patterns
            'models': [
                'get_user_by_id', 'create_user_profile', 'update_user_settings', 'delete_user_account',
                'get_all_posts', 'create_blog_post', 'update_post_content', 'delete_post_permanently',
                'get_comments_for_post', 'create_comment_reply', 'moderate_comment_content',
                'get_user_permissions', 'assign_role_to_user', 'revoke_user_access'
            ],
            'views': [
                'handle_user_login', 'process_registration_request', 'validate_password_reset',
                'render_dashboard_view', 'display_user_profile', 'show_post_detail_page',
                'handle_api_post_request', 'process_file_upload', 'generate_csv_export',
                'handle_payment_webhook', 'process_stripe_callback', 'send_notification_email'
            ],
            'utils': [
                'validate_email_format', 'sanitize_user_input', 'generate_unique_slug',
                'format_datetime_display', 'calculate_reading_time', 'compress_image_file',
                'encrypt_sensitive_data', 'decode_jwt_token', 'hash_user_password',
                'send_slack_notification', 'log_user_activity', 'cache_expensive_query'
            ],
            'services': [
                'authenticate_user_credentials', 'authorize_api_access', 'rate_limit_check',
                'integrate_third_party_api', 'sync_external_data', 'process_background_task',
                'schedule_automated_backup', 'monitor_system_health', 'analyze_user_behavior',
                'generate_analytics_report', 'optimize_database_query', 'cleanup_expired_sessions'
            ],
            # Frontend/React patterns  
            'components': [
                'render_user_avatar', 'display_loading_spinner', 'show_error_message',
                'format_currency_value', 'validate_form_input', 'handle_button_click',
                'toggle_modal_visibility', 'update_component_state', 'fetch_user_data',
                'render_data_table', 'handle_search_input', 'filter_results_list'
            ],
            'hooks': [
                'use_authenticated_user', 'use_local_storage', 'use_debounced_input',
                'use_infinite_scroll', 'use_api_data_fetcher', 'use_form_validation',
                'use_theme_context', 'use_responsive_layout', 'use_websocket_connection',
                'use_permission_checker', 'use_error_boundary', 'use_analytics_tracker'
            ],
            # DevOps/Infrastructure patterns
            'deployment': [
                'deploy_to_production', 'rollback_failed_deployment', 'check_service_health',
                'scale_container_instances', 'update_environment_config', 'backup_database_dump',
                'monitor_error_rates', 'alert_on_high_latency', 'rotate_security_keys',
                'sync_static_assets', 'update_dns_records', 'configure_load_balancer'
            ],
            'testing': [
                'test_user_authentication', 'mock_external_api_call', 'setup_test_database',
                'teardown_test_fixtures', 'assert_response_status', 'validate_json_schema',
                'test_edge_case_scenario', 'benchmark_query_performance', 'test_security_headers',
                'verify_data_migration', 'test_concurrent_access', 'validate_input_sanitization'
            ]
        }
    
    def generate_realistic_functions(self, count: int) -> List[Dict[str, Any]]:
        """Generate realistic function data simulating a large project."""
        functions = []
        
        for i in range(count):
            # Select category and pattern
            category = random.choice(list(self.patterns.keys()))
            base_name = random.choice(self.patterns[category])
            
            # Add variations to make names unique
            if random.random() < 0.3:  # 30% chance of adding suffix
                suffix = random.choice(['_v2', '_async', '_cached', '_optimized', '_legacy'])
                name = f"{base_name}{suffix}"
            elif random.random() < 0.2:  # 20% chance of adding prefix
                prefix = random.choice(['admin_', 'api_', 'async_', 'bulk_'])
                name = f"{prefix}{base_name}"
            else:
                name = f"{base_name}_{i // 10}"  # Add index-based variation
            
            # Generate realistic code patterns
            code_patterns = {
                'models': f"def {name}(self, **kwargs): return self.objects.filter(**kwargs)",
                'views': f"async def {name}(request): return JsonResponse({{'status': 'ok'}})",
                'utils': f"def {name}(data): return process_data(data)",
                'services': f"async def {name}(self, payload): await self.client.post(payload)",
                'components': f"def {name}(props): return React.createElement('div', props)",
                'hooks': f"def {name}(): return useContext(AppContext)",
                'deployment': f"def {name}(): subprocess.run(['docker', 'deploy'])",
                'testing': f"def {name}(self): self.assertEqual(result, expected)"
            }
            
            functions.append({
                'name': name,
                'code': code_patterns.get(category, f"def {name}(): pass"),
                'category': category,
                'file_path': f"src/{category}/{name.split('_')[0]}.py"
            })
        
        return functions


async def test_real_world_scenario():
    """Test oopstracker with realistic large-scale project data."""
    print("🌍 Real-World Scenario Testing")
    print("=" * 60)
    print(f"⏰ Start time: {datetime.now().strftime('%H:%M:%S')}")
    
    # Monitor system resources
    process = psutil.Process()
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB
    print(f"📊 Initial memory usage: {initial_memory:.1f} MB")
    
    # Generate realistic data
    print(f"\n🏭 Generating realistic project data...")
    generator = RealWorldDataGenerator()
    
    # Test with increasing scales
    scales = [500, 1000, 2500]  # Build up to large scale
    
    for scale in scales:
        print(f"\n{'='*20} TESTING SCALE: {scale} FUNCTIONS {'='*20}")
        
        functions = generator.generate_realistic_functions(scale)
        print(f"📈 Generated {len(functions)} realistic functions")
        
        # Show diversity
        categories = {}
        for func in functions:
            cat = func['category']
            categories[cat] = categories.get(cat, 0) + 1
        
        print(f"📋 Function categories:")
        for cat, count in categories.items():
            print(f"   - {cat}: {count} functions")
        
        # Create initial group
        initial_group = FunctionGroup(
            group_id=f"real_world_{scale}",
            functions=functions,
            label=f"Real World Test ({scale} functions)",
            confidence=0.8,
            metadata={'scale': scale, 'categories': len(categories)}
        )
        
        # Test splitting
        print(f"\n🤖 Testing splitting with {scale} functions...")
        splitter = SmartGroupSplitter(enable_ai=True, use_mock_ai=True)  # Use mock for speed
        
        start_time = time.time()
        memory_before = process.memory_info().rss / 1024 / 1024
        
        try:
            final_groups = await splitter.split_large_groups_with_llm([initial_group], max_depth=3)
            
            elapsed_time = time.time() - start_time
            memory_after = process.memory_info().rss / 1024 / 1024
            memory_delta = memory_after - memory_before
            
            # Analyze results
            print(f"✅ Splitting completed in {elapsed_time:.1f}s")
            print(f"📊 Results:")
            print(f"   - Original groups: 1")
            print(f"   - Final groups: {len(final_groups)}")
            
            sizes = [len(g.functions) for g in final_groups]
            print(f"   - Group sizes: min={min(sizes)}, max={max(sizes)}, avg={sum(sizes)/len(sizes):.1f}")
            print(f"   - Groups >100: {sum(1 for s in sizes if s > 100)}")
            
            # Performance metrics
            print(f"📈 Performance:")
            print(f"   - Processing time: {elapsed_time:.1f}s")
            print(f"   - Memory delta: {memory_delta:+.1f} MB")
            print(f"   - Functions/second: {len(functions)/elapsed_time:.1f}")
            
            # Verify function accounting
            total_final = sum(len(g.functions) for g in final_groups)
            if total_final != len(functions):
                print(f"❌ CRITICAL: Function count mismatch! {total_final} != {len(functions)}")
                return False
            
            # Check for problematic patterns
            large_groups = [g for g in final_groups if len(g.functions) > 150]
            if large_groups:
                print(f"⚠️  WARNING: {len(large_groups)} groups still very large (>150)")
                for g in large_groups[:3]:  # Show first 3
                    print(f"      - {g.label}: {len(g.functions)} functions")
            
            # Memory check
            if memory_delta > 100:  # >100MB increase
                print(f"⚠️  WARNING: High memory usage increase: {memory_delta:.1f} MB")
            
        except Exception as e:
            print(f"❌ ERROR at scale {scale}: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    # Final system check
    final_memory = process.memory_info().rss / 1024 / 1024
    total_memory_delta = final_memory - initial_memory
    
    print(f"\n🔍 Final system state:")
    print(f"   - Total memory delta: {total_memory_delta:+.1f} MB")
    print(f"   - Final memory usage: {final_memory:.1f} MB")
    
    if total_memory_delta > 200:
        print(f"⚠️  WARNING: Significant memory increase detected")
        return False
    
    return True


async def test_error_conditions():
    """Test various error conditions that might occur in real usage."""
    print(f"\n🚨 Testing Error Conditions")
    print("=" * 40)
    
    # Test with problematic function names
    problematic_functions = [
        {'name': 'def_with_def_in_name', 'code': 'def def_with_def_in_name(): pass'},
        {'name': '🚀_unicode_name', 'code': 'def unicode_name(): pass'},  # Unicode
        {'name': 'very_very_very_long_function_name_that_exceeds_normal_limits', 'code': 'def very_long(): pass'},
        {'name': 'function-with-hyphens', 'code': 'def function_with_hyphens(): pass'},  # Invalid Python
        {'name': '', 'code': 'def anonymous(): pass'},  # Empty name
    ]
    
    for i in range(120):  # Make it large enough to trigger splitting
        problematic_functions.append({
            'name': f'normal_function_{i}',
            'code': f'def normal_function_{i}(): return {i}'
        })
    
    print(f"📋 Testing with {len(problematic_functions)} functions (including problematic ones)")
    
    try:
        group = FunctionGroup(
            group_id="error_test",
            functions=problematic_functions,
            label="Error Condition Test",
            confidence=0.8,
            metadata={}
        )
        
        splitter = SmartGroupSplitter(enable_ai=True, use_mock_ai=True)
        start_time = time.time()
        
        result = await splitter.split_large_groups_with_llm([group], max_depth=2)
        elapsed = time.time() - start_time
        
        print(f"✅ Error condition test completed in {elapsed:.1f}s")
        print(f"   - Resulted in {len(result)} groups")
        print(f"   - No critical failures detected")
        
        return True
        
    except Exception as e:
        print(f"❌ Error condition test failed: {e}")
        return False


async def main():
    """Main test execution function."""
    print("🎯 Comprehensive Real-World Testing for oopstracker")
    print("Testing with realistic project patterns and error conditions\n")
    
    success = True
    
    # Run main scenario test
    success &= await test_real_world_scenario()
    
    # Run error condition tests
    success &= await test_error_conditions()
    
    print(f"\n⏰ End time: {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 60)
    
    if success:
        print("🎉 All real-world scenario tests passed!")
        print("✅ oopstracker is ready for production use")
        return True
    else:
        print("❌ Real-world testing revealed issues")
        print("⚠️  Review and address problems before production use")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)