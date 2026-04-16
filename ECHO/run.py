import subprocess
import time
import sys
import os

processes = []


def start_system():
    print("🚀 正在启动 E.C.H.O. 神经哨兵系统...")

    # 🌟 核心防弹修复：获取 run.py 所在的绝对物理路径
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    python_exe = sys.executable

    print(f"📂 锚定工作目录: {BASE_DIR}")

    # 1. 启动虚拟脑电发生器 (Producer)
    print("📡 [1/3] 启动虚拟脑电数据流...")
    p_producer = subprocess.Popen(
        [python_exe, "virtual_eeg_producer.py"],
        cwd=BASE_DIR,  # 强制绑定工作目录
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
    )
    processes.append(p_producer)
    time.sleep(2)

    # 2. 启动核心引擎与 FastAPI (Core)
    print("🧠 [2/3] 启动核心分析引擎与 API 服务...")
    p_core = subprocess.Popen(
        [python_exe, "echo_core.py"],
        cwd=BASE_DIR,  # 强制绑定工作目录
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
    )
    processes.append(p_core)
    time.sleep(3)

    # 3. 启动 Streamlit 前端 (App)
    print("👁️ [3/3] 启动可视化中控台...")
    p_app = subprocess.Popen(
        [python_exe, "-m", "streamlit", "run", "echo_app.py", "--server.port", "8501", "--server.headless", "false"],
        cwd=BASE_DIR,  # 强制绑定工作目录
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
    )
    processes.append(p_app)

    print("\n✅ 系统已全量上线！")
    print("🔗 API 文档: http://127.0.0.1:8000/docs")
    print("🔗 可视化终端: http://127.0.0.1:8501")
    print("⌨️  在终端中按下 Ctrl+C 停止所有服务\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        shutdown_system()


def shutdown_system():
    print("\n🛑 收到中断信号，正在优雅关闭所有组件...")
    for p in processes:
        try:
            p.terminate()
            p.wait(timeout=2)
        except Exception:
            p.kill()
    print("👋 所有服务已安全退出。")


if __name__ == "__main__":
    start_system()