#!/usr/bin/env python3
"""
最终版 Chatchat 启动脚本
"""

import sys
import os
import asyncio
from pathlib import Path

def main():
    print("=== Langchain-Chatchat 启动器 ===")
    
    # 设置路径
    current_dir = Path(__file__).parent
    chatchat_server_path = current_dir / "Langchain-Chatchat" / "libs" / "chatchat-server"
    sys.path.insert(0, str(chatchat_server_path))
    print(f"✓ 已设置路径: {chatchat_server_path}")
    
    try:
        # 应用 Pydantic 修复
        print("正在应用 Pydantic v2 兼容性修复...")
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
        print("正在测试关键模块...")
        from chatchat.server.agent.tools_factory.tools_registry import regist_tool
        print("✓ tools_registry 导入成功")
        
        # 直接调用异步启动函数
        print("正在启动 Chatchat 服务器...")
        print("=" * 40)
        
        from chatchat.startup import start_main_server
        
        # 创建参数对象
        class Args:
            def __init__(self):
                self.all = True
                self.api = False
                self.webui = False
        
        args = Args()
        
        # 运行异步函数
        if sys.version_info >= (3, 7):
            asyncio.run(start_main_server(args))
        else:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(start_main_server(args))
        
    except KeyboardInterrupt:
        print("\n用户中断，正在退出...")
    except Exception as e:
        print(f"启动失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    main()
