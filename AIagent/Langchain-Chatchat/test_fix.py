#!/usr/bin/env python3
"""
Test script to verify the Pydantic v2 compatibility fix works
"""

import sys
import os

# Add the local chatchat-server to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'Langchain-Chatchat', 'libs', 'chatchat-server'))

def test_import():
    """Test if the tools_registry import works after applying the fix"""
    try:
        print("Testing import of tools_registry...")
        from chatchat.server.agent.tools_factory.tools_registry import regist_tool
        print("✓ Import successful! The fix works.")
        return True
    except Exception as e:
        print(f"✗ Import failed: {e}")
        return False

def test_basetool_config():
    """Test BaseTool configuration"""
    try:
        from langchain_core.tools import BaseTool
        print(f"BaseTool has model_config: {hasattr(BaseTool, 'model_config')}")
        if hasattr(BaseTool, 'model_config'):
            print(f"model_config: {BaseTool.model_config}")
        print(f"BaseTool has Config: {hasattr(BaseTool, 'Config')}")
        return True
    except Exception as e:
        print(f"Error checking BaseTool: {e}")
        return False

if __name__ == "__main__":
    print("Testing Pydantic v2 compatibility fix...")
    print("=" * 50)
    
    test_basetool_config()
    print()
    test_import()
    
    print("=" * 50)
    print("Test completed.")
