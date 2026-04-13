#!/usr/bin/env python3
"""
启动脚本：直接从源码运行 Langchain-Chatchat
解决 Pydantic v2 兼容性问题并启动应用
"""

import sys
import os
from pathlib import Path

def setup_environment():
    """设置环境和路径"""
    # 获取当前脚本所在目录
    current_dir = Path(__file__).parent
    
    # 添加 chatchat-server 到 Python 路径
    chatchat_server_path = current_dir / "Langchain-Chatchat" / "libs" / "chatchat-server"
    
    if not chatchat_server_path.exists():
        print(f"错误：找不到 chatchat-server 目录: {chatchat_server_path}")
        return False
    
    # 将路径添加到 sys.path 的开头，确保优先使用本地版本
    sys.path.insert(0, str(chatchat_server_path))
    print(f"已添加路径到 Python path: {chatchat_server_path}")
    
    return True

def apply_pydantic_fix():
    """应用 Pydantic v2 兼容性修复"""
    try:
        print("正在应用 Pydantic v2 兼容性修复...")
        
        from langchain_core.tools import BaseTool
        from chatchat.server.pydantic_v1 import Extra
        
        # 应用修复
        try:
            # 尝试 Pydantic v1 风格（向后兼容）
            BaseTool.Config.extra = Extra.allow
            print("✓ 应用了 Pydantic v1 风格配置")
        except AttributeError:
            # Pydantic v2 风格
            from pydantic import ConfigDict
            if not hasattr(BaseTool, 'model_config'):
                BaseTool.model_config = ConfigDict(extra='allow')
                print("✓ 应用了 Pydantic v2 风格配置（新建 model_config）")
            else:
                # 更新现有的 model_config
                if isinstance(BaseTool.model_config, dict):
                    BaseTool.model_config['extra'] = 'allow'
                    print("✓ 应用了 Pydantic v2 风格配置（更新字典）")
                else:
                    # 如果是 ConfigDict，创建一个新的
                    BaseTool.model_config = ConfigDict(**BaseTool.model_config, extra='allow')
                    print("✓ 应用了 Pydantic v2 风格配置（更新 ConfigDict）")
        
        return True
        
    except Exception as e:
        print(f"✗ 应用修复时出错: {e}")
        return False

def start_chatchat():
    """启动 chatchat 应用"""
    try:
        print("正在启动 Chatchat...")
        print("=" * 60)
        
        # 导入并运行 chatchat
        from chatchat.cli import main
        
        # 模拟命令行参数
        sys.argv = ['chatchat', 'start', '-a']
        
        # 启动应用
        main()
        
    except KeyboardInterrupt:
        print("\n用户中断，正在退出...")
    except Exception as e:
        print(f"启动 Chatchat 时出错: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

def main():
    """主函数"""
    print("Langchain-Chatchat 启动器")
    print("=" * 60)
    
    # 1. 设置环境
    if not setup_environment():
        print("环境设置失败，退出")
        sys.exit(1)
    
    # 2. 应用修复
    if not apply_pydantic_fix():
        print("修复应用失败，退出")
        sys.exit(1)
    
    # 3. 启动应用
    print("准备启动应用...")
    start_chatchat()

if __name__ == "__main__":
    main()
