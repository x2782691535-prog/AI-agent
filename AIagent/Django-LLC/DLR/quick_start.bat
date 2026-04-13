@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:: DLR + LangChain-Chatchat Windows快速启动脚本

echo ================================================================================
echo 🚀 DLR + LangChain-Chatchat 快速启动 (Windows)
echo ================================================================================
echo 📊 知识图谱构建 + 🤖 智能问答 + 📚 知识库管理
echo ================================================================================
echo.

:: 检查Python
echo 🔍 检查Python环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python未安装或未添加到PATH
    echo    请从 https://python.org 下载并安装Python 3.8+
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo ✅ Python版本: %PYTHON_VERSION%

:: 检查Git
echo 🔍 检查Git...
git --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Git未安装或未添加到PATH
    echo    请从 https://git-scm.com 下载并安装Git
    pause
    exit /b 1
)
echo ✅ Git已安装

:: 检查端口占用
echo 🔍 检查端口占用...
netstat -an | findstr ":8000 " >nul
if not errorlevel 1 (
    echo ⚠️ 端口8000已被占用
) else (
    echo ✅ 端口8000可用
)

netstat -an | findstr ":7861 " >nul
if not errorlevel 1 (
    echo ⚠️ 端口7861已被占用
) else (
    echo ✅ 端口7861可用
)

:: 创建虚拟环境
if exist venv (
    echo ✅ 虚拟环境已存在
) else (
    echo 📦 创建Python虚拟环境...
    python -m venv venv
    if errorlevel 1 (
        echo ❌ 虚拟环境创建失败
        pause
        exit /b 1
    )
    echo ✅ 虚拟环境创建完成
)

:: 激活虚拟环境
echo 🔧 激活虚拟环境...
call venv\Scripts\activate.bat

:: 升级pip
echo 📦 升级pip...
python -m pip install --upgrade pip

:: 安装DLR依赖
echo 📦 安装DLR依赖...
pip install -r requirements.txt
if errorlevel 1 (
    echo ❌ DLR依赖安装失败
    pause
    exit /b 1
)
echo ✅ DLR依赖安装完成

:: 克隆Chatchat项目
if exist Langchain-Chatchat (
    echo ✅ Chatchat项目已存在
) else (
    echo 📥 克隆LangChain-Chatchat项目...
    git clone https://github.com/chatchat-space/Langchain-Chatchat.git
    if errorlevel 1 (
        echo ❌ Chatchat项目克隆失败
        pause
        exit /b 1
    )
    echo ✅ Chatchat项目克隆完成
)

:: 安装Chatchat
echo 📦 安装LangChain-Chatchat...
cd Langchain-Chatchat
pip install -e .
if errorlevel 1 (
    echo ❌ Chatchat安装失败
    pause
    exit /b 1
)

:: 初始化Chatchat配置
if exist configs\model_config.py (
    echo ✅ Chatchat配置已存在
) else (
    echo ⚙️ 初始化Chatchat配置...
    python copy_config_example.py
    echo ✅ Chatchat配置初始化完成
)

cd ..

:: 创建环境变量文件
if exist .env (
    echo ✅ 环境变量文件已存在
) else (
    echo ⚙️ 创建环境变量文件...
    (
        echo # DLR环境配置
        echo DEBUG=True
        echo SECRET_KEY=your-secret-key-change-in-production
        echo.
        echo # 数据库配置
        echo DB_NAME=dlr_db
        echo DB_USER=dlr_user
        echo DB_PASSWORD=dlr_password
        echo DB_HOST=localhost
        echo DB_PORT=3306
        echo.
        echo # Neo4j配置
        echo NEO4J_URI=bolt://localhost:7687
        echo NEO4J_USER=neo4j
        echo NEO4J_PASSWORD=neo4j_password
        echo.
        echo # Chatchat配置
        echo CHATCHAT_API_BASE_URL=http://127.0.0.1:7861
        echo.
        echo # 其他配置
        echo ALLOWED_HOSTS=localhost,127.0.0.1
    ) > .env
    echo ✅ 环境变量文件创建完成
    echo ⚠️ 请根据需要修改 .env 文件中的配置
)

:: 初始化数据库
echo 🗄️ 初始化数据库...
python manage.py makemigrations
python manage.py migrate
if errorlevel 1 (
    echo ❌ 数据库初始化失败
    echo    请确保MySQL服务已启动并配置正确
    pause
    exit /b 1
)
echo ✅ 数据库初始化完成

:: 创建启动脚本
echo 📝 创建启动脚本...

:: 创建Chatchat启动脚本
(
    echo @echo off
    echo chcp 65001 ^>nul
    echo cd /d "%~dp0"
    echo call venv\Scripts\activate.bat
    echo cd Langchain-Chatchat
    echo echo 🚀 启动Chatchat服务...
    echo echo ⏳ 请等待服务启动完成...
    echo python startup.py -a
) > start_chatchat.bat

:: 创建DLR启动脚本
(
    echo @echo off
    echo chcp 65001 ^>nul
    echo cd /d "%~dp0"
    echo call venv\Scripts\activate.bat
    echo echo 🚀 启动DLR服务...
    echo echo 🌐 访问地址:
    echo echo    - DLR主界面: http://localhost:8000
    echo echo    - Chatchat界面: http://localhost:8501
    echo echo    - API文档: http://localhost:7861/docs
    echo echo.
    echo echo 按 Ctrl+C 停止服务
    echo python manage.py runserver 8000
) > start_dlr.bat

:: 创建完整启动脚本
(
    echo @echo off
    echo chcp 65001 ^>nul
    echo cd /d "%~dp0"
    echo echo ================================================================================
    echo echo 🚀 启动DLR + LangChain-Chatchat 完整系统
    echo echo ================================================================================
    echo echo.
    echo echo 🔄 启动Chatchat服务...
    echo start "Chatchat服务" start_chatchat.bat
    echo echo ⏳ 等待Chatchat启动...
    echo timeout /t 15 /nobreak ^>nul
    echo echo.
    echo echo 🔄 启动DLR服务...
    echo call start_dlr.bat
) > start_all.bat

echo ✅ 启动脚本创建完成

echo.
echo ================================================================================
echo 🎉 安装完成！
echo ================================================================================
echo.
echo 📋 启动选项:
echo   1. start_all.bat      - 启动完整系统 (推荐)
echo   2. start_chatchat.bat - 仅启动Chatchat
echo   3. start_dlr.bat      - 仅启动DLR
echo.
echo 🌐 访问地址:
echo   - DLR主界面: http://localhost:8000
echo   - Chatchat界面: http://localhost:8501  
echo   - API文档: http://localhost:7861/docs
echo.
echo 📖 详细文档: COMPLETE_DEPLOYMENT_GUIDE.md
echo.

:: 询问是否立即启动
set /p START_NOW="是否立即启动完整系统? (y/N): "
if /i "%START_NOW%"=="y" (
    echo.
    echo 🚀 正在启动系统...
    call start_all.bat
) else (
    echo.
    echo 💡 稍后可以运行 start_all.bat 启动系统
)

echo.
echo 按任意键退出...
pause >nul
