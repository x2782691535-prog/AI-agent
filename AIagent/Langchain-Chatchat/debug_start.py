#!/usr/bin/env python3
"""
调试版 Chatchat 启动脚本
"""

import sys
import os
from pathlib import Path

def main():
    print("=== Chatchat 调试启动器 ===")
    
    # 设置路径
    current_dir = Path(__file__).parent
    chatchat_server_path = current_dir / "Langchain-Chatchat" / "libs" / "chatchat-server"
    
    print(f"当前目录: {current_dir}")
    print(f"Chatchat 路径: {chatchat_server_path}")
    print(f"路径存在: {chatchat_server_path.exists()}")
    
    if not chatchat_server_path.exists():
        print("错误：路径不存在！")
        return False
    
    # 添加到 Python 路径
    sys.path.insert(0, str(chatchat_server_path))
    print("✓ 已添加路径到 sys.path")
    
    try:
        # 应用修复
        print("正在应用 Pydantic 修复...")
        from langchain_core.tools import BaseTool
        from chatchat.server.pydantic_v1 import Extra
        
        try:
            BaseTool.Config.extra = Extra.allow
            print("✓ Pydantic v1 修复成功")
        except AttributeError:
            from pydantic import ConfigDict
            BaseTool.model_config = ConfigDict(extra='allow')
            print("✓ Pydantic v2 修复成功")
        
        # 测试导入
        print("测试关键模块导入...")
        from chatchat.server.agent.tools_factory.tools_registry import regist_tool
        print("✓ tools_registry 导入成功")
        
        from chatchat.startup import main as startup_main
        print("✓ startup.main 导入成功")
        
        # 启动应用
        print("正在启动应用...")
        print("模拟命令行调用: chatchat start -a")

        # 模拟命令行参数
        import sys
        original_argv = sys.argv.copy()
        sys.argv = ['chatchat', 'start', '-a']

        try:
            startup_main()
        finally:
            sys.argv = original_argv
        
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    main()
