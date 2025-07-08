"""
Tests for OOPStracker CLI.
"""

import pytest
import tempfile
import os
from unittest.mock import patch, MagicMock
from io import StringIO
import sys

from oopstracker.cli import main, scan_file, setup_logging


class TestCLI:
    """Test CLI functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test.db")
        self.test_file = os.path.join(self.temp_dir, "test.py")
        
        # Create test file
        with open(self.test_file, 'w') as f:
            f.write('def hello(): print("Hello")')
    
    def teardown_method(self):
        """Clean up test environment."""
        if os.path.exists(self.test_file):
            os.remove(self.test_file)
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        os.rmdir(self.temp_dir)
    
    def test_scan_file_new_code(self):
        """Test scanning a new file."""
        from oopstracker.core import CodeMemory
        
        memory = CodeMemory(db_path=self.db_path)
        
        # Capture stdout
        old_stdout = sys.stdout
        sys.stdout = captured_output = StringIO()
        
        try:
            records = scan_file(self.test_file, memory)
            output = captured_output.getvalue()
            
            assert len(records) == 1
            assert "✅ Registered:" in output
            assert self.test_file in output
            
        finally:
            sys.stdout = old_stdout
    
    def test_scan_file_duplicate(self):
        """Test scanning a file with duplicate code."""
        from oopstracker.core import CodeMemory
        
        memory = CodeMemory(db_path=self.db_path)
        
        # Register code first
        with open(self.test_file, 'r') as f:
            code = f.read()
        memory.register(code, file_path=self.test_file)
        
        # Capture stdout
        old_stdout = sys.stdout
        sys.stdout = captured_output = StringIO()
        
        try:
            records = scan_file(self.test_file, memory)
            output = captured_output.getvalue()
            
            assert len(records) == 0
            assert "⚠️  DUPLICATE detected" in output
            
        finally:
            sys.stdout = old_stdout
    
    def test_scan_file_nonexistent(self):
        """Test scanning non-existent file."""
        from oopstracker.core import CodeMemory
        
        memory = CodeMemory(db_path=self.db_path)
        
        # Capture stdout
        old_stdout = sys.stdout
        sys.stdout = captured_output = StringIO()
        
        try:
            records = scan_file("nonexistent.py", memory)
            output = captured_output.getvalue()
            
            assert len(records) == 0
            assert "❌ Error scanning" in output
            
        finally:
            sys.stdout = old_stdout
    
    @patch('sys.argv', ['oopstracker', '--help'])
    def test_help_command(self):
        """Test help command."""
        with pytest.raises(SystemExit):
            main()
    
    @patch('sys.argv', ['oopstracker', 'check', 'def hello(): pass'])
    def test_check_command(self):
        """Test check command."""
        # Capture stdout
        old_stdout = sys.stdout
        sys.stdout = captured_output = StringIO()
        
        try:
            main()
            output = captured_output.getvalue()
            
            assert "✅ No duplicates found" in output
            
        finally:
            sys.stdout = old_stdout
    
    @patch('sys.argv', ['oopstracker', 'register', 'def hello(): pass', '--function-name', 'hello'])
    def test_register_command(self):
        """Test register command."""
        # Capture stdout
        old_stdout = sys.stdout
        sys.stdout = captured_output = StringIO()
        
        try:
            main()
            output = captured_output.getvalue()
            
            assert "✅ Registered code with hash:" in output
            
        finally:
            sys.stdout = old_stdout
    
    @patch('sys.argv', ['oopstracker', 'list'])
    def test_list_command(self):
        """Test list command."""
        # Capture stdout
        old_stdout = sys.stdout
        sys.stdout = captured_output = StringIO()
        
        try:
            main()
            output = captured_output.getvalue()
            
            assert "📋 Found" in output
            
        finally:
            sys.stdout = old_stdout
    
    @patch('sys.argv', ['oopstracker', 'clear', '--yes'])
    def test_clear_command(self):
        """Test clear command."""
        # Capture stdout
        old_stdout = sys.stdout
        sys.stdout = captured_output = StringIO()
        
        try:
            main()
            output = captured_output.getvalue()
            
            assert "✅ Memory cleared successfully" in output
            
        finally:
            sys.stdout = old_stdout
    
    def test_setup_logging_info(self):
        """Test setting up INFO logging."""
        import logging
        
        # Clear any existing handlers
        logging.getLogger().handlers = []
        
        setup_logging("INFO")
        
        # Check that logging was configured
        assert len(logging.getLogger().handlers) > 0
        assert logging.getLogger().level == logging.INFO
    
    def test_setup_logging_debug(self):
        """Test setting up DEBUG logging."""
        import logging
        
        # Clear any existing handlers
        logging.getLogger().handlers = []
        
        setup_logging("DEBUG")
        
        # Check that logging was configured
        assert len(logging.getLogger().handlers) > 0
        assert logging.getLogger().level == logging.DEBUG