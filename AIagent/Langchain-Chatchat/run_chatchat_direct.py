#!/usr/bin/env python3
"""
直接运行 Chatchat 的脚本，无需安装
"""

import sys
import os
from pathlib import Path

# 设置路径
current_dir = Path(__file__).parent
chatchat_server_path = current_dir / "Langchain-Chatchat" / "libs" / "chatchat-server"

# 添加到 Python 路径
sys.path.insert(0, str(chatchat_server_path))

print("Langchain-Chatchat 直接启动")
print("=" * 50)
print(f"使用源码路径: {chatchat_server_path}")

try:
    # 应用 Pydantic 修复
    print("正在应用 Pydantic v2 兼容性修复...")
    
    from langchain_core.tools import BaseTool
    from chatchat.server.pydantic_v1 import Extra
    
    try:
        BaseTool.Config.extra = Extra.allow
        print("✓ 应用了 Pydantic v1 风格配置")
    except AttributeError:
        from pydantic import ConfigDict
        BaseTool.model_config = ConfigDict(extra='allow')
        print("✓ 应用了 Pydantic v2 风格配置")
    
    # 导入启动模块
    print("正在导入启动模块...")
    from chatchat import startup
    
    # 启动服务器
    print("正在启动 Chatchat 服务器...")
    print("=" * 50)
    
    # 调用启动函数
    startup.start_main_server()
    
except KeyboardInterrupt:
    print("\n用户中断，正在退出...")
except Exception as e:
    print(f"启动失败: {e}")
    import traceback
    traceback.print_exc()
