#!/usr/bin/env python3
"""
修复版 Chatchat 启动脚本
解决 Pydantic v2 兼容性问题并启动应用
"""

import sys
import os
from pathlib import Path

def main():
    print("Langchain-Chatchat 修复版启动器")
    print("=" * 50)
    
    # 设置路径
    current_dir = Path(__file__).parent
    chatchat_server_path = current_dir / "Langchain-Chatchat" / "libs" / "chatchat-server"
    
    if not chatchat_server_path.exists():
        print(f"错误：找不到 chatchat-server 目录: {chatchat_server_path}")
        return False
    
    # 添加到 Python 路径
    sys.path.insert(0, str(chatchat_server_path))
    print(f"已添加路径: {chatchat_server_path}")
    
    try:
        # 应用 Pydantic v2 兼容性修复
        print("正在应用 Pydantic v2 兼容性修复...")
        
        from langchain_core.tools import BaseTool
        from chatchat.server.pydantic_v1 import Extra
        
        try:
            # 尝试 Pydantic v1 风格
            BaseTool.Config.extra = Extra.allow
            print("✓ 应用了 Pydantic v1 风格配置")
        except AttributeError:
            # Pydantic v2 风格
            from pydantic import ConfigDict
            BaseTool.model_config = ConfigDict(extra='allow')
            print("✓ 应用了 Pydantic v2 风格配置")
        
        # 测试导入
        print("正在测试修复效果...")
        from chatchat.server.agent.tools_factory.tools_registry import regist_tool
        print("✓ tools_registry 导入成功！")
        
        # 启动应用
        print("正在启动 Chatchat 应用...")
        print("=" * 50)

        # 导入并启动 - 使用正确的 main 函数
        from chatchat.startup import main

        # 创建参数对象，模拟 chatchat start -a 命令
        class Args:
            def __init__(self):
                self.all = True
                self.api = False
                self.webui = False

        # 调用 main 函数
        main(all=True, api=False, webui=False)
        
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
