#!/usr/bin/env python3
"""
Comprehensive Testing Script for Prompt Vault Plugin
Tests all functionality that Flow Launcher expects, including handling of NoneType errors
"""

import json
import os
import sys
import subprocess
import tempfile
import shutil
from pathlib import Path
import time

# Add the plugin directory to path to import main
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the plugin
try:
    from main import PromptVaultPlugin, handle_jsonrpc_request
    PLUGIN_IMPORT_SUCCESS = True
except ImportError as e:
    print(f"❌ CRITICAL: Cannot import plugin - {e}")
    PLUGIN_IMPORT_SUCCESS = False


class PromptVaultTester:
    """Comprehensive tester for Prompt Vault plugin"""
    
    def __init__(self):
        self.test_results = []
        self.temp_dir = None
        self.test_prompts_file = None
        self.setup_test_environment()
    
    def setup_test_environment(self):
        """Setup temporary test environment"""
        try:
            # Create temporary directory
            self.temp_dir = tempfile.mkdtemp(prefix="prompt_vault_test_")
            self.test_prompts_file = os.path.join(self.temp_dir, "prompts.json")
            
            # Create test prompts data
            test_data = {
                "prompts": [
                    {
                        "id": 1,
                        "title": "Test Email Template",
                        "prompt": "Write a professional email about: {{topic}}",
                        "tags": ["email", "professional", "template"],
                        "use_case": "communication"
                    },
                    {
                        "id": 2,
                        "title": "Code Review Helper",
                        "prompt": "Review this code for best practices:\n\n{{code}}",
                        "tags": ["code", "review", "programming"],
                        "use_case": "development"
                    },
                    {
                        "id": 3,
                        "title": "Meeting Notes",
                        "prompt": "Summarize meeting notes: {{notes}}",
                        "tags": ["meeting", "summary", "notes"],
                        "use_case": "documentation"
                    }
                ],
                "metadata": {
                    "version": "1.0",
                    "last_updated": "2025-05-30T10:00:00Z"
                }
            }
            
            # Write test data
            with open(self.test_prompts_file, 'w', encoding='utf-8') as f:
                json.dump(test_data, f, indent=2)
            
            print(f"✅ Test environment setup complete")
            print(f"   Temp dir: {self.temp_dir}")
            print(f"   Test file: {self.test_prompts_file}")
            
        except Exception as e:
            print(f"❌ Failed to setup test environment: {e}")
            return False
        
        return True
    
    def cleanup_test_environment(self):
        """Cleanup temporary test environment"""
        try:
            if self.temp_dir and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
                print(f"✅ Test environment cleaned up")
        except Exception as e:
            print(f"⚠️  Warning: Could not cleanup test environment: {e}")
    
    def run_test(self, test_name, test_func, *args, **kwargs):
        """Run a test and record results"""
        print(f"\n🧪 Running test: {test_name}")
        try:
            result = test_func(*args, **kwargs)
            if result:
                print(f"✅ PASS: {test_name}")
                self.test_results.append(("PASS", test_name, None))
                return True
            else:
                print(f"❌ FAIL: {test_name}")
                self.test_results.append(("FAIL", test_name, "Test returned False"))
                return False
        except Exception as e:
            print(f"❌ ERROR: {test_name} - {e}")
            self.test_results.append(("ERROR", test_name, str(e)))
            return False
    
    def test_plugin_import(self):
        """Test that plugin can be imported"""
        return PLUGIN_IMPORT_SUCCESS
    
    def test_plugin_initialization(self):
        """Test plugin can be initialized"""
        try:
            plugin = PromptVaultPlugin()
            return plugin is not None
        except Exception:
            return False
    
    def test_prompts_file_loading(self):
        """Test loading prompts from file"""
        try:
            plugin = PromptVaultPlugin()
            # Temporarily override the file path for testing
            plugin.prompts_file_path = self.test_prompts_file
            success = plugin._load_prompts()
            return success and len(plugin.prompts_data) == 3
        except Exception:
            return False
    
    def test_search_functionality(self):
        """Test search across different fields"""
        try:
            plugin = PromptVaultPlugin()
            plugin.prompts_file_path = self.test_prompts_file
            plugin._load_prompts()
            
            # Test title search
            results = plugin._search_prompts("email")
            if len(results) != 1 or results[0]['title'] != "Test Email Template":
                return False
            
            # Test tag search
            results = plugin._search_prompts("programming")
            if len(results) != 1 or results[0]['title'] != "Code Review Helper":
                return False
            
            # Test multi-word search
            results = plugin._search_prompts("meeting notes")
            if len(results) != 1 or results[0]['title'] != "Meeting Notes":
                return False
            
            # Test no results
            results = plugin._search_prompts("nonexistent")
            if len(results) != 0:
                return False
            
            return True
        except Exception:
            return False
    
    def test_jsonrpc_query_request(self):
        """Test JSON-RPC query request handling"""
        try:
            # Create request
            request = {
                "method": "query",
                "parameters": ["email"]
            }
            request_json = json.dumps(request)
            
            # Override file path by temporarily replacing the function
            original_get_path = PromptVaultPlugin._get_prompts_file_path
            PromptVaultPlugin._get_prompts_file_path = lambda self: self.test_prompts_file
            
            try:
                # Handle request with prompts_file_path
                response = handle_jsonrpc_request(request_json, self.test_prompts_file)
                
                # Validate response
                if not isinstance(response, dict):
                    print(f"❌ Response is not a dict: {response}")
                    return False
                
                if "result" not in response:
                    print(f"❌ Missing 'result' key in response: {response}")
                    return False
                
                results = response["result"]
                if not isinstance(results, list):
                    print(f"❌ 'result' is not a list: {results}")
                    return False
                
                if len(results) != 1:
                    print(f"❌ Expected 1 result, got {len(results)}")
                    return False
                
                result = results[0]
                if result.get("Title") != "Test Email Template":
                    print(f"❌ Title mismatch: {result.get('Title')}")
                    return False
                
                if not isinstance(result.get("JsonRPCAction"), dict):
                    print(f"❌ Invalid JsonRPCAction type: {result.get('JsonRPCAction')}")
                    return False
                
                if result["JsonRPCAction"].get("method") != "copy_prompt":
                    print(f"❌ Invalid method in JsonRPCAction: {result['JsonRPCAction'].get('method')}")
                    return False
                
                if not isinstance(result["JsonRPCAction"].get("parameters"), list):
                    print(f"❌ Invalid parameters type in JsonRPCAction: {result['JsonRPCAction'].get('parameters')}")
                    return False
                
                return True
            finally:
                # Restore original function
                PromptVaultPlugin._get_prompts_file_path = original_get_path
                
        except Exception as e:
            print(f"Error in test_jsonrpc_query_request: {e}")
            return False
    
    def test_jsonrpc_copy_action(self):
        """Test JSON-RPC copy action handling"""
        try:
            # Create copy action request
            context_data = json.dumps({
                "prompt": "Test prompt text",
                "title": "Test Title"
            })
            
            request = {
                "method": "copy_prompt",
                "parameters": [context_data]
            }
            request_json = json.dumps(request)
            
            # Handle request
            response = handle_jsonrpc_request(request_json)
            
            # Validate response (should return empty result for actions)
            if not isinstance(response, dict):
                return False
            
            if "result" not in response:
                return False
            
            if not isinstance(response["result"], list):
                return False
            
            return True
        except Exception:
            return False
    
    def test_clipboard_operations(self):
        """Test clipboard copy functionality"""
        try:
            plugin = PromptVaultPlugin()
            test_text = "Test clipboard content"
            
            # Test clipboard copy
            success = plugin._copy_to_clipboard(test_text)
            
            # Note: We can't reliably test if text was actually copied 
            # without external dependencies, but we can test the method runs
            return True  # As long as no exception is thrown
        except Exception:
            return False
    
    def test_error_handling(self):
        """Test error handling for various scenarios"""
        try:
            plugin = PromptVaultPlugin()
            
            # Test with non-existent file
            plugin.prompts_file_path = "/nonexistent/path/prompts.json"
            success = plugin._load_prompts()
            if success:  # Should fail gracefully
                return False
            
            # Test query with no prompts loaded
            results = plugin.query("test")
            if not isinstance(results, list) or len(results) != 1:
                return False
            
            if "No prompts found" not in results[0]["Title"]:
                return False
            
            return True
        except Exception:
            return False
    
    def test_json_output_format(self):
        """Test that all JSON output is valid"""
        try:
            # Override file path
            original_get_path = PromptVaultPlugin._get_prompts_file_path
            PromptVaultPlugin._get_prompts_file_path = lambda self: self.test_prompts_file
            
            try:
                # Test various requests
                test_requests = [
                    '{"method": "query", "parameters": ["email"]}',
                    '{"method": "query", "parameters": [""]}',
                    '{"method": "copy_prompt", "parameters": ["{\"prompt\": \"test\", \"title\": \"test\"}"]}',
                    'invalid json',
                    ''
                ]
                
                for request in test_requests:
                    response = handle_jsonrpc_request(request, self.test_prompts_file)
                    
                    # Validate response is valid JSON
                    try:
                        json_str = json.dumps(response)
                        parsed = json.loads(json_str)
                    except (json.JSONDecodeError, TypeError) as e:
                        print(f"❌ Invalid JSON response for request '{request}': {e}")
                        return False
                    
                    # Validate basic structure
                    if not isinstance(parsed, dict):
                        print(f"❌ Response is not a dict for request '{request}'")
                        return False
                    
                    # Validate result structure
                    if "result" not in parsed:
                        print(f"❌ Missing 'result' key in response for request '{request}'")
                        return False
                    
                    if not isinstance(parsed["result"], list):
                        print(f"❌ 'result' is not a list for request '{request}'")
                        return False
                    
                    # Validate individual results
                    for result in parsed["result"]:
                        if not isinstance(result, dict):
                            print(f"❌ Result item is not a dict for request '{request}'")
                            return False
                        
                        if "Title" not in result:
                            print(f"❌ Missing 'Title' in result for request '{request}'")
                            return False
                        
                        if "IcoPath" not in result:
                            print(f"❌ Missing 'IcoPath' in result for request '{request}'")
                            return False
                        
                        if "JsonRPCAction" in result:
                            if not isinstance(result["JsonRPCAction"], dict):
                                print(f"❌ Invalid JsonRPCAction type for request '{request}'")
                                return False
                            if "method" not in result["JsonRPCAction"]:
                                print(f"❌ Missing 'method' in JsonRPCAction for request '{request}'")
                                return False
                            if "parameters" not in result["JsonRPCAction"]:
                                print(f"❌ Missing 'parameters' in JsonRPCAction for request '{request}'")
                                return False
                    
                return True
            finally:
                PromptVaultPlugin._get_prompts_file_path = original_get_path
                
        except Exception as e:
            print(f"❌ Error in test_json_output_format: {e}")
            return False

    def test_none_type_query_handling(self):
        """
        Test that if PromptVaultPlugin.query() returns None (simulating a bug),
        handle_jsonrpc_request() returns a valid 'Invalid Response Format' error result
        rather than propagating NoneType and causing an unhandled exception.
        """
        try:
            # Monkeypatch PromptVaultPlugin.query to return None
            original_query = PromptVaultPlugin.query
            PromptVaultPlugin.query = lambda self, q: None
            
            try:
                request = {
                    "method": "query",
                    "parameters": ["anything"]
                }
                request_json = json.dumps(request)
                response = handle_jsonrpc_request(request_json, self.test_prompts_file)
                
                # The response should be a dict with "result" key
                if not isinstance(response, dict):
                    print(f"❌ Response is not a dict: {response}")
                    return False
                
                results = response.get("result", [])
                if not isinstance(results, list) or len(results) != 1:
                    print(f"❌ 'result' is not a single-item list for NoneType scenario: {results}")
                    return False
                
                error_item = results[0]
                # Check that the Title indicates invalid response format
                if error_item.get("Title") != "Invalid Response Format":
                    print(f"❌ Incorrect Title for NoneType handling: {error_item.get('Title')}")
                    return False
                
                # SubTitle should reference "Query returned invalid format"
                if "Query returned invalid format" not in error_item.get("SubTitle", ""):
                    print(f"❌ SubTitle does not mention invalid format: {error_item.get('SubTitle')}")
                    return False
                
                # IcoPath should still be present
                if "IcoPath" not in error_item:
                    print(f"❌ Missing IcoPath in error response: {error_item}")
                    return False
                
                return True
            finally:
                # Restore original method
                PromptVaultPlugin.query = original_query
        except Exception as e:
            print(f"❌ Error in test_none_type_query_handling: {e}")
            return False

    def test_flow_launcher_simulation(self):
        """Simulate exactly what Flow Launcher does"""
        try:
            # Prepare the plugin file path
            main_py_path = os.path.join(os.path.dirname(__file__), "main.py")
            if not os.path.exists(main_py_path):
                print(f"❌ main.py not found at {main_py_path}")
                return False
            
            # Create a temporary prompts file in the same directory
            temp_prompts = os.path.join(os.path.dirname(main_py_path), "prompts.json")
            shutil.copy2(self.test_prompts_file, temp_prompts)
            
            try:
                # Test query via subprocess (exactly like Flow Launcher)
                test_query = '{"method": "query", "parameters": ["email"]}'
                
                process = subprocess.Popen(
                    [sys.executable, main_py_path],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    cwd=os.path.dirname(main_py_path)
                )
                
                stdout, stderr = process.communicate(input=test_query, timeout=10)
                
                if process.returncode != 0:
                    print(f"❌ Process failed with return code {process.returncode}")
                    if stderr:
                        print(f"❌ STDERR: {stderr}")
                    return False
                
                if stderr:
                    print(f"⚠️  STDERR (warnings): {stderr}")
                
                # Validate output
                try:
                    response = json.loads(stdout)
                    if "result" not in response:
                        print(f"❌ Invalid response structure: {response}")
                        return False
                    
                    results = response["result"]
                    if not isinstance(results, list) or len(results) == 0:
                        print(f"❌ No results returned: {results}")
                        return False
                    
                    first_result = results[0]
                    if "Title" not in first_result:
                        print(f"❌ Result missing Title: {first_result}")
                        return False
                    
                    print(f"✅ Flow Launcher simulation successful")
                    print(f"   Query: {test_query}")
                    print(f"   Response: {json.dumps(response, indent=2)}")
                    
                    return True
                    
                except json.JSONDecodeError as e:
                    print(f"❌ Invalid JSON response: {e}")
                    print(f"   Raw output: {stdout}")
                    return False
                    
            finally:
                # Cleanup temporary prompts file
                if os.path.exists(temp_prompts):
                    os.remove(temp_prompts)
                    
        except subprocess.TimeoutExpired:
            print(f"❌ Process timed out")
            return False
        except Exception as e:
            print(f"❌ Simulation failed: {e}")
            return False
    
    def run_all_tests(self):
        """Run all tests and report results"""
        print("🚀 Starting Prompt Vault Plugin Tests")
        print("=" * 50)
        
        # Run all tests
        tests = [
            ("Plugin Import", self.test_plugin_import),
            ("Plugin Initialization", self.test_plugin_initialization),
            ("Prompts File Loading", self.test_prompts_file_loading),
            ("Search Functionality", self.test_search_functionality),
            ("JSON-RPC Query Request", self.test_jsonrpc_query_request),
            ("JSON-RPC Copy Action", self.test_jsonrpc_copy_action),
            ("Clipboard Operations", self.test_clipboard_operations),
            ("Error Handling", self.test_error_handling),
            ("JSON Output Format", self.test_json_output_format),
            ("NoneType Query Handling", self.test_none_type_query_handling),
            ("Flow Launcher Simulation", self.test_flow_launcher_simulation),
        ]
        
        for test_name, test_func in tests:
            self.run_test(test_name, test_func)
        
        # Print summary
        print("\n" + "=" * 50)
        print("📊 TEST RESULTS SUMMARY")
        print("=" * 50)
        
        passed = sum(1 for result in self.test_results if result[0] == "PASS")
        failed = sum(1 for result in self.test_results if result[0] in ["FAIL", "ERROR"])
        total = len(self.test_results)
        
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Success Rate: {(passed/total)*100:.1f}%")
        
        if failed > 0:
            print("\n❌ FAILED TESTS:")
            for status, name, error in self.test_results:
                if status in ["FAIL", "ERROR"]:
                    print(f"   - {name}: {error or 'Unknown error'}")
        
        print("\n" + "=" * 50)
        
        if passed == total:
            print("🎉 ALL TESTS PASSED! Plugin is ready for Flow Launcher.")
            return True
        else:
            print("❌ SOME TESTS FAILED! Plugin needs fixes before using with Flow Launcher.")
            return False


def main():
    """Main testing function"""
    tester = PromptVaultTester()
    
    try:
        success = tester.run_all_tests()
        return 0 if success else 1
    finally:
        tester.cleanup_test_environment()


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
