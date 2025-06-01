#!/usr/bin/env python3
"""
Prompt Vault - Flow Launcher Plugin
Improved final version with better display and auto-paste
"""

import json
import os
import sys
import time
import subprocess
import re
from pathlib import Path

# Optional imports - graceful degradation if not available
try:
    import pyperclip
    CLIPBOARD_AVAILABLE = True
except ImportError:
    CLIPBOARD_AVAILABLE = False

try:
    import pyautogui
    AUTOPASTE_AVAILABLE = True
    pyautogui.FAILSAFE = False
except ImportError:
    AUTOPASTE_AVAILABLE = False


class PromptVaultPlugin:
    """Self-contained Flow Launcher plugin for prompt management"""
    
    def __init__(self, prompts_file_path=None):
        """Initialize plugin with optional prompts file path"""
        self.prompts_data = []
        self.prompts_file_path = prompts_file_path or self._get_prompts_file_path()
        self.last_error = None
        self._load_prompts()
    
    def _get_prompts_file_path(self):
        """Get the path to prompts.json file"""
        try:
            # Try Dropbox location first
            home_dir = Path.home()
            dropbox_path = home_dir / "Dropbox" / "PromptVault" / "prompts.json"
            
            if dropbox_path.exists():
                return str(dropbox_path)
            
            # Fallback to plugin directory
            script_dir = Path(__file__).resolve().parent
            local_path = script_dir / "prompts.json"
            return str(local_path)
        except Exception:
            return "prompts.json"
    
    def _load_prompts(self):
        """Load prompts from JSON file with error handling"""
        try:
            if not self.prompts_file_path:
                return False
                
            if os.path.exists(self.prompts_file_path):
                with open(self.prompts_file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.prompts_data = data.get('prompts', [])
                    return True
            else:
                self.prompts_data = []
                return False
        except Exception:
            self.prompts_data = []
            return False
    
    def _clean_preview_text(self, text):
        """Clean prompt text for preview display"""
        if not text:
            return "No description available"
        
        # Remove template variables like {{variable}} for cleaner preview
        cleaned = re.sub(r'\{\{[^}]+\}\}', '[variable]', text)
        
        # Remove excessive whitespace and newlines
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        # Truncate and add ellipsis if needed
        if len(cleaned) > 80:
            cleaned = cleaned[:77] + "..."
        
        return cleaned if cleaned else "Template prompt"
    
    def _search_prompts(self, query_terms):
        """Search prompts across all fields with relevance ranking"""
        if not query_terms:
            return self.prompts_data[:10]  # Return first 10 if no search terms
        
        query_lower = query_terms.lower()
        search_terms = query_lower.split()
        
        exact_matches = []
        partial_matches = []
        
        for prompt in self.prompts_data:
            # Combine all searchable fields
            searchable_text = ' '.join([
                prompt.get('title', ''),
                prompt.get('prompt', ''),
                ' '.join(prompt.get('tags', [])),
                prompt.get('use_case', '')
            ]).lower()
            
            # Check for exact phrase match
            if query_lower in searchable_text:
                exact_matches.append(prompt)
            # Check if all search terms are present
            elif all(term in searchable_text for term in search_terms):
                partial_matches.append(prompt)
        
        # Combine results with exact matches first
        results = exact_matches + partial_matches
        return results[:10]  # Limit to 10 results for performance
    
    def _copy_to_clipboard_fallback(self, text):
        """Fallback clipboard copy using subprocess"""
        try:
            # Use Windows built-in clip command
            process = subprocess.Popen(['clip'], stdin=subprocess.PIPE, text=True)
            process.communicate(input=text)
            return process.returncode == 0
        except Exception:
            return False
    
    def _copy_to_clipboard(self, text):
        """Copy text to clipboard with multiple fallback methods"""
        # Try pyperclip first
        if CLIPBOARD_AVAILABLE:
            try:
                pyperclip.copy(text)
                return True
            except Exception:
                pass
        
        # Fallback to Windows clip command
        return self._copy_to_clipboard_fallback(text)
    
    def _auto_paste_windows_api(self):
        """Auto-paste using Windows API through Python ctypes"""
        try:
            import ctypes
            
            # Get current window
            user32 = ctypes.windll.user32
            
            # Send Ctrl+V using Windows API
            VK_CONTROL = 0x11
            VK_V = 0x56
            KEYEVENTF_KEYUP = 0x0002
            
            # Press Ctrl
            user32.keybd_event(VK_CONTROL, 0, 0, 0)
            # Press V
            user32.keybd_event(VK_V, 0, 0, 0)
            # Release V
            user32.keybd_event(VK_V, 0, KEYEVENTF_KEYUP, 0)
            # Release Ctrl
            user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)
            
            return True
        except Exception:
            return False
    
    def _auto_paste_sendkeys(self):
        """Auto-paste using Windows SendKeys via COM"""
        try:
            import win32com.client
            shell = win32com.client.Dispatch("WScript.Shell")
            shell.SendKeys("^v")
            return True
        except Exception:
            return False
    
    def _auto_paste_hidden_powershell(self):
        """Auto-paste using hidden PowerShell window"""
        try:
            # Use hidden PowerShell window to avoid flashing
            script = """
            Add-Type -AssemblyName System.Windows.Forms
            [System.Windows.Forms.SendKeys]::SendWait("^v")
            """
            
            process = subprocess.Popen([
                'powershell.exe',
                '-WindowStyle', 'Hidden',
                '-NoProfile',
                '-ExecutionPolicy', 'Bypass',
                '-Command', script
            ], 
            creationflags=subprocess.CREATE_NO_WINDOW,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
            )
            
            process.wait(timeout=3)
            return process.returncode == 0
        except Exception:
            return False
    
    def _auto_paste(self):
        """Attempt to auto-paste with multiple fallback methods"""
        # Small delay to ensure clipboard is ready
        time.sleep(0.1)
        
        # Try pyautogui first (most reliable)
        if AUTOPASTE_AVAILABLE:
            try:
                pyautogui.hotkey('ctrl', 'v')
                return True
            except Exception:
                pass
        
        # Try Windows API method
        try:
            if self._auto_paste_windows_api():
                return True
        except Exception:
            pass
        
        # Try COM SendKeys method
        try:
            if self._auto_paste_sendkeys():
                return True
        except Exception:
            pass
        
        # Try hidden PowerShell as last resort
        try:
            return self._auto_paste_hidden_powershell()
        except Exception:
            return False
    
    def query(self, query_text):
        """Handle search query and return results"""
        try:
            # Load prompts
            load_success = self._load_prompts()
            
            if not load_success or not self.prompts_data:
                return [{
                    "Title": "No prompts found",
                    "SubTitle": f"Check if prompts.json exists at: {self.prompts_file_path}",
                    "IcoPath": "Images\\app.png"
                }]
            
            # Search prompts
            results = self._search_prompts(query_text)
            
            if not results:
                return [{
                    "Title": "No matching prompts",
                    "SubTitle": f"No prompts found for: {query_text}",
                    "IcoPath": "Images\\app.png"
                }]
            
            # Format results for Flow Launcher
            formatted_results = []
            for prompt in results:
                title = prompt.get('title', 'Untitled Prompt')
                prompt_text = prompt.get('prompt', '')
                
                # Create clean preview text
                preview = self._clean_preview_text(prompt_text)
                
                # Add tags if available
                tags = prompt.get('tags', [])
                if tags:
                    tags_str = ', '.join(tags)
                    subtitle = f"{preview} | Tags: {tags_str}"
                else:
                    subtitle = preview
                
                # Create context data for the action
                context_data = json.dumps({
                    "prompt": prompt_text,
                    "title": title
                })
                
                formatted_results.append({
                    "Title": title,
                    "SubTitle": subtitle,
                    "IcoPath": "Images\\app.png",
                    "JsonRPCAction": {
                        "method": "copy_prompt",
                        "parameters": [context_data]
                    }
                })
            
            return formatted_results
            
        except Exception as e:
            return [{
                "Title": "Error occurred",
                "SubTitle": f"Plugin error: {str(e)}",
                "IcoPath": "Images\\app.png"
            }]
    
    def copy_prompt(self, context_data):
        """Copy prompt to clipboard and attempt auto-paste"""
        try:
            # Parse context data
            data = json.loads(context_data)
            prompt_text = data.get('prompt', '')
            
            # Copy to clipboard
            copy_success = self._copy_to_clipboard(prompt_text)
            
            if copy_success:
                # Attempt auto-paste with a slight delay
                time.sleep(0.2)  # Give Flow Launcher time to close
                self._auto_paste()
            
            return []
            
        except Exception:
            return []


def handle_jsonrpc_request(request_data):
    """Handle JSON-RPC request from Flow Launcher"""
    try:
        # Initialize plugin
        plugin = PromptVaultPlugin()
        
        if not request_data:
            return {"result": []}
        
        # Parse JSON request
        try:
            request = json.loads(request_data)
            method = request.get('method', '')
            parameters = request.get('parameters', [])
        except json.JSONDecodeError:
            # If not valid JSON, treat as query string
            method = 'query'
            parameters = [str(request_data)]
        
        if method == 'query':
            query_text = parameters[0] if parameters else ""
            results = plugin.query(query_text)
            return {"result": results}
            
        elif method == 'copy_prompt':
            context_data = parameters[0] if parameters else ""
            results = plugin.copy_prompt(context_data)
            return {"result": results}
        
        else:
            return {"result": []}
            
    except Exception as e:
        return {
            "result": [{
                "Title": "Plugin Error",
                "SubTitle": f"Error: {str(e)}",
                "IcoPath": "Images\\app.png"
            }]
        }


def main():
    """Main entry point for Flow Launcher communication"""
    try:
        # Get input from command line arguments (Flow Launcher uses argv[1])
        input_data = ""
        if len(sys.argv) > 1:
            input_data = sys.argv[1]
        
        if not input_data:
            # No input, return empty result
            response = {"result": []}
        else:
            # Handle the request
            response = handle_jsonrpc_request(input_data)
        
        # Output JSON response
        print(json.dumps(response, ensure_ascii=False))
        sys.stdout.flush()
        
    except Exception as e:
        # Emergency fallback
        error_response = {
            "result": [{
                "Title": "Critical Error",
                "SubTitle": f"Error: {str(e)}",
                "IcoPath": "Images\\app.png"
            }]
        }
        print(json.dumps(error_response, ensure_ascii=False))
        sys.stdout.flush()


if __name__ == "__main__":
    main()