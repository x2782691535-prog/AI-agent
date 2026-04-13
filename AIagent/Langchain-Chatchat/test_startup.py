#!/usr/bin/env python3
"""
测试启动脚本
"""

import sys
import os
from pathlib import Path

def main():
    print("测试 Chatchat 启动")
    print("=" * 30)
    
    # 设置路径
    current_dir = Path(__file__).parent
    chatchat_server_path = current_dir / "libs" / "chatchat-server"
    sys.path.insert(0, str(chatchat_server_path))
    
    try:
        # 应用修复
        print("1. 应用 Pydantic 修复...")
        from langchain_core.tools import BaseTool
        from chatchat.server.pydantic_v1 import Extra
        
        try:
            BaseTool.Config.extra = Extra.allow
            print("   ✓ Pydantic v1 风格")
        except AttributeError:
            from pydantic import ConfigDict
            BaseTool.model_config = ConfigDict(extra='allow')
            print("   ✓ Pydantic v2 风格")
        
        # 测试导入
        print("2. 测试关键模块导入...")
        from chatchat.server.agent.tools_factory.tools_registry import regist_tool
        print("   ✓ tools_registry")
        
        from chatchat import startup
        print("   ✓ startup 模块")
        
        print("3. 所有测试通过！")
        print("=" * 30)
        print("现在可以尝试启动应用了")
        
        # 询问是否启动
        response = input("是否现在启动 Chatchat？(y/n): ")
        if response.lower() == 'y':
            print("正在启动...")
            startup.start_main_server()
        else:
            print("测试完成，未启动应用")
        
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
