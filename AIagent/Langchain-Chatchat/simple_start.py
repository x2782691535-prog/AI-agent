#!/usr/bin/env python3
"""
简化版 Chatchat 启动脚本
"""

import sys
import os

print("Langchain-Chatchat 启动器")
print("=" * 40)

# 添加路径
sys.path.insert(0, 'Langchain-Chatchat/libs/chatchat-server')
print("已设置 Python 路径")

try:
    # 应用 Pydantic 修复
    print("正在应用 Pydantic v2 修复...")
    from langchain_core.tools import BaseTool
    from chatchat.server.pydantic_v1 import Extra
    
    try:
        BaseTool.Config.extra = Extra.allow
        print("✓ 修复成功 (Pydantic v1 风格)")
    except AttributeError:
        from pydantic import ConfigDict
        BaseTool.model_config = ConfigDict(extra='allow')
        print("✓ 修复成功 (Pydantic v2 风格)")
    
    # 测试导入
    print("正在测试导入...")
    from chatchat.server.agent.tools_factory.tools_registry import regist_tool
    print("✓ tools_registry 导入成功")
    
    # 启动应用
    print("正在启动 Chatchat...")
    print("=" * 40)
    
    from chatchat.startup import start_main_server
    start_main_server()
    
except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()
