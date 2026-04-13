#!/usr/bin/env python
"""
DLR + LangChain-Chatchat 快速启动脚本
一键安装和启动完整系统
"""

import os
import sys
import subprocess
import time
import requests
import threading
from pathlib import Path

class QuickStart:
    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.venv_dir = self.base_dir / "venv"
        self.chatchat_dir = self.base_dir / "Langchain-Chatchat"
        
    def print_banner(self):
        """显示启动横幅"""
        print("=" * 80)
        print("🚀 DLR + LangChain-Chatchat 快速启动")
        print("=" * 80)
        print("📊 知识图谱构建 + 🤖 智能问答 + 📚 知识库管理")
        print("=" * 80)
        print()
    
    def check_python(self):
        """检查Python版本"""
        print("🔍 检查Python环境...")
        
        if sys.version_info < (3, 8):
            print("❌ Python版本需要 >= 3.8")
            print(f"   当前版本: {sys.version}")
            sys.exit(1)
        
        print(f"✅ Python版本: {sys.version_info.major}.{sys.version_info.minor}")
    
    def check_ports(self):
        """检查端口占用"""
        print("🔍 检查端口占用...")
        
        ports = {
            8000: "DLR主服务",
            7861: "Chatchat API",
            8501: "Chatchat UI"
        }
        
        for port, service in ports.items():
            try:
                response = requests.get(f"http://localhost:{port}", timeout=1)
                print(f"⚠️ 端口 {port} ({service}) 已被占用")
            except:
                print(f"✅ 端口 {port} ({service}) 可用")
    
    def run_command(self, cmd, cwd=None, shell=True):
        """运行命令"""
        try:
            result = subprocess.run(
                cmd, 
                shell=shell, 
                cwd=cwd, 
                capture_output=True, 
                text=True,
                check=True
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            print(f"❌ 命令执行失败: {cmd}")
            print(f"   错误: {e.stderr}")
            return None
    
    def create_venv(self):
        """创建虚拟环境"""
        if self.venv_dir.exists():
            print("✅ 虚拟环境已存在")
            return
        
        print("📦 创建Python虚拟环境...")
        self.run_command(f"python -m venv {self.venv_dir}")
        print("✅ 虚拟环境创建完成")
    
    def get_pip_cmd(self):
        """获取pip命令"""
        if os.name == 'nt':  # Windows
            return str(self.venv_dir / "Scripts" / "pip")
        else:  # Linux/Mac
            return str(self.venv_dir / "bin" / "pip")
    
    def get_python_cmd(self):
        """获取Python命令"""
        if os.name == 'nt':  # Windows
            return str(self.venv_dir / "Scripts" / "python")
        else:  # Linux/Mac
            return str(self.venv_dir / "bin" / "python")
    
    def install_dlr_deps(self):
        """安装DLR依赖"""
        print("📦 安装DLR依赖...")
        
        pip_cmd = self.get_pip_cmd()
        
        # 升级pip
        self.run_command(f"{pip_cmd} install --upgrade pip")
        
        # 安装依赖
        result = self.run_command(f"{pip_cmd} install -r requirements.txt")
        if result is None:
            print("❌ DLR依赖安装失败")
            sys.exit(1)
        
        print("✅ DLR依赖安装完成")
    
    def clone_chatchat(self):
        """克隆Chatchat项目"""
        if self.chatchat_dir.exists():
            print("✅ Chatchat项目已存在")
            return
        
        print("📥 克隆LangChain-Chatchat项目...")
        result = self.run_command(
            "git clone https://github.com/chatchat-space/Langchain-Chatchat.git",
            cwd=self.base_dir
        )
        
        if result is None:
            print("❌ Chatchat项目克隆失败")
            sys.exit(1)
        
        print("✅ Chatchat项目克隆完成")
    
    def install_chatchat(self):
        """安装Chatchat"""
        print("📦 安装LangChain-Chatchat...")
        
        pip_cmd = self.get_pip_cmd()
        
        # 安装Chatchat
        result = self.run_command(f"{pip_cmd} install -e .", cwd=self.chatchat_dir)
        if result is None:
            print("❌ Chatchat安装失败")
            sys.exit(1)
        
        # 初始化配置
        python_cmd = self.get_python_cmd()
        config_file = self.chatchat_dir / "configs" / "model_config.py"
        
        if not config_file.exists():
            print("⚙️ 初始化Chatchat配置...")
            self.run_command(f"{python_cmd} copy_config_example.py", cwd=self.chatchat_dir)
        
        print("✅ Chatchat安装完成")
    
    def setup_env(self):
        """设置环境变量"""
        env_file = self.base_dir / ".env"
        
        if env_file.exists():
            print("✅ 环境变量文件已存在")
            return
        
        print("⚙️ 创建环境变量文件...")
        
        env_content = """# DLR环境配置
DEBUG=True
SECRET_KEY=your-secret-key-change-in-production

# 数据库配置
DB_NAME=dlr_db
DB_USER=dlr_user
DB_PASSWORD=dlr_password
DB_HOST=localhost
DB_PORT=3306

# Neo4j配置
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=neo4j_password

# Chatchat配置
CHATCHAT_API_BASE_URL=http://127.0.0.1:7861

# 其他配置
ALLOWED_HOSTS=localhost,127.0.0.1
"""
        
        with open(env_file, 'w', encoding='utf-8') as f:
            f.write(env_content)
        
        print("✅ 环境变量文件创建完成")
        print("⚠️ 请根据需要修改 .env 文件中的配置")
    
    def init_database(self):
        """初始化数据库"""
        print("🗄️ 初始化数据库...")
        
        python_cmd = self.get_python_cmd()
        
        # Django迁移
        self.run_command(f"{python_cmd} manage.py makemigrations", cwd=self.base_dir)
        self.run_command(f"{python_cmd} manage.py migrate", cwd=self.base_dir)
        
        print("✅ 数据库初始化完成")
    
    def start_chatchat(self):
        """启动Chatchat服务"""
        print("🚀 启动Chatchat服务...")
        
        python_cmd = self.get_python_cmd()
        
        def run_chatchat():
            subprocess.run(
                f"{python_cmd} startup.py -a",
                shell=True,
                cwd=self.chatchat_dir
            )
        
        # 在后台线程启动Chatchat
        chatchat_thread = threading.Thread(target=run_chatchat, daemon=True)
        chatchat_thread.start()
        
        # 等待Chatchat启动
        print("⏳ 等待Chatchat启动...")
        for i in range(30):
            try:
                response = requests.get("http://localhost:7861/health", timeout=2)
                if response.status_code == 200:
                    print("✅ Chatchat服务启动成功")
                    return True
            except:
                pass
            
            time.sleep(2)
            print(f"   等待中... ({i+1}/30)")
        
        print("⚠️ Chatchat启动超时，但可能仍在启动中")
        return False
    
    def start_dlr(self):
        """启动DLR服务"""
        print("🚀 启动DLR服务...")
        
        python_cmd = self.get_python_cmd()
        
        print("✅ DLR服务启动中...")
        print("🌐 访问地址:")
        print("   - DLR主界面: http://localhost:8000")
        print("   - Chatchat界面: http://localhost:8501")
        print("   - API文档: http://localhost:7861/docs")
        print()
        print("按 Ctrl+C 停止服务")
        print("=" * 80)
        
        try:
            subprocess.run(
                f"{python_cmd} manage.py runserver 8000",
                shell=True,
                cwd=self.base_dir
            )
        except KeyboardInterrupt:
            print("\n🛑 服务已停止")
    
    def run(self):
        """运行快速启动"""
        self.print_banner()
        
        # 检查环境
        self.check_python()
        self.check_ports()
        
        # 安装和配置
        self.create_venv()
        self.install_dlr_deps()
        self.clone_chatchat()
        self.install_chatchat()
        self.setup_env()
        self.init_database()
        
        print("\n" + "=" * 80)
        print("🎉 安装完成！正在启动服务...")
        print("=" * 80)
        
        # 启动服务
        self.start_chatchat()
        time.sleep(5)  # 给Chatchat更多启动时间
        self.start_dlr()

def main():
    """主函数"""
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help']:
        print("DLR + LangChain-Chatchat 快速启动脚本")
        print()
        print("用法:")
        print("  python quick_start.py")
        print()
        print("功能:")
        print("  - 自动安装所有依赖")
        print("  - 自动配置环境")
        print("  - 启动完整系统")
        print()
        print("访问地址:")
        print("  - DLR主界面: http://localhost:8000")
        print("  - Chatchat界面: http://localhost:8501")
        print("  - API文档: http://localhost:7861/docs")
        return
    
    try:
        quick_start = QuickStart()
        quick_start.run()
    except KeyboardInterrupt:
        print("\n🛑 安装被用户中断")
    except Exception as e:
        print(f"\n❌ 安装失败: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
