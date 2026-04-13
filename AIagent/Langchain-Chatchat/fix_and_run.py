#!/usr/bin/env python3
"""
Fix for Pydantic v2 compatibility issue in Langchain-Chatchat
This script applies the fix and then runs the chatchat application.
"""

import sys
import os

# Add the local chatchat-server to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'Langchain-Chatchat', 'libs', 'chatchat-server'))

def apply_pydantic_fix():
    """Apply the Pydantic v2 compatibility fix"""
    try:
        from langchain_core.tools import BaseTool
        from chatchat.server.pydantic_v1 import Extra
        
        # Apply the fix for Pydantic v2 compatibility
        try:
            # Try Pydantic v1 style first (for backward compatibility)
            BaseTool.Config.extra = Extra.allow
            print("Applied Pydantic v1 style configuration")
        except AttributeError:
            # Pydantic v2 style - set model_config if it doesn't exist or update it
            from pydantic import ConfigDict
            if not hasattr(BaseTool, 'model_config'):
                BaseTool.model_config = ConfigDict(extra='allow')
                print("Applied Pydantic v2 style configuration (new model_config)")
            else:
                # Update existing model_config
                if isinstance(BaseTool.model_config, dict):
                    BaseTool.model_config['extra'] = 'allow'
                    print("Applied Pydantic v2 style configuration (updated dict)")
                else:
                    # If it's a ConfigDict, create a new one with the extra setting
                    BaseTool.model_config = ConfigDict(**BaseTool.model_config, extra='allow')
                    print("Applied Pydantic v2 style configuration (updated ConfigDict)")
        
        return True
    except Exception as e:
        print(f"Error applying fix: {e}")
        return False

def main():
    """Main function to apply fix and run chatchat"""
    print("Applying Pydantic v2 compatibility fix...")
    
    if not apply_pydantic_fix():
        print("Failed to apply fix. Exiting.")
        sys.exit(1)
    
    print("Fix applied successfully. Starting chatchat...")
    
    try:
        # Import and run chatchat
        import chatchat.startup
        chatchat.startup.start_main_server()
    except Exception as e:
        print(f"Error starting chatchat: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
