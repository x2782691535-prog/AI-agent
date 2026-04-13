# 🚀 DLR 知识图谱系统 + LangChain-Chatchat

> **完整的AI知识管理解决方案**  
> 知识图谱构建 + 智能问答 + 知识库管理 + 可视化展示

## ✨ 功能特性

### 🎯 核心功能
- **📊 知识图谱构建**: 文档解析、实体识别、关系抽取、图谱生成
- **🎨 交互式可视化**: 力导向、层次、环形等多种布局
- **🤖 智能问答**: 基于知识图谱和知识库的综合问答
- **📚 知识库管理**: 文档向量化存储和语义检索
- **👥 用户管理**: 多用户支持、权限控制
- **📄 文档处理**: 支持PDF、Word、TXT等格式

### 🌟 集成优势
- **双引擎驱动**: DLR知识图谱 + Chatchat智能问答
- **数据互通**: 知识图谱和知识库数据共享
- **统一界面**: 一个平台管理所有功能
- **API丰富**: 完整的RESTful API接口

## 🚀 快速开始

### 🎯 一键启动（推荐）

#### Windows用户
```bash
# 双击运行或命令行执行
quick_start.bat
```

#### Linux/Mac用户
```bash
# Python脚本启动
python quick_start.py

# 或使用Shell脚本
chmod +x deploy_with_chatchat.sh
./deploy_with_chatchat.sh -m dev
```

### ⚡ 快速启动特性
- ✅ **自动环境检查**: Python、Git、端口占用
- ✅ **自动依赖安装**: DLR + Chatchat所有依赖
- ✅ **自动配置**: 环境变量、数据库初始化
- ✅ **自动启动**: 同时启动所有服务
- ✅ **5分钟完成**: 从零到运行的完整体验

## 🌐 访问地址

启动成功后，可以通过以下地址访问：

- **🏠 DLR主界面**: http://localhost:8000
- **💬 Chatchat界面**: http://localhost:8501
- **📚 API文档**: http://localhost:7861/docs
- **🔧 管理后台**: http://localhost:8000/admin

## 📋 系统要求

### 基础环境
- **Python**: 3.8 - 3.11
- **操作系统**: Windows 10+, Ubuntu 18.04+, macOS 10.15+
- **内存**: 8GB+ (推荐16GB+)
- **存储**: 10GB+ 可用空间

### 数据库（可选）
- **MySQL**: 8.0+ (生产环境推荐)
- **Neo4j**: 5.0+ (知识图谱存储)
- **SQLite**: 内置支持 (开发环境)

## 🛠️ 手动安装

如果快速启动脚本无法使用，可以按照以下步骤手动安装：

### 1. 克隆项目
```bash
git clone <your-repo-url>
cd DLR
```

### 2. 安装DLR
```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows

# 安装依赖
pip install -r requirements.txt
```

### 3. 安装Chatchat
```bash
# 克隆Chatchat
git clone https://github.com/chatchat-space/Langchain-Chatchat.git
cd Langchain-Chatchat

# 安装Chatchat
pip install -e .

# 初始化配置
python copy_config_example.py
cd ..
```

### 4. 配置环境
```bash
# 复制环境变量模板
cp .env.example .env

# 编辑配置文件
# 设置数据库连接、Neo4j配置等
```

### 5. 初始化数据库
```bash
python manage.py migrate
python manage.py createsuperuser
```

### 6. 启动服务
```bash
# 终端1: 启动Chatchat
cd Langchain-Chatchat
python startup.py -a

# 终端2: 启动DLR
cd ..
python manage.py runserver 8000
```

## 🔧 系统检查

使用系统状态检查脚本验证所有服务是否正常：

```bash
python check_system_status.py
```

检查内容包括：
- ✅ DLR服务状态
- ✅ Chatchat服务状态  
- ✅ 数据库连接
- ✅ Neo4j连接
- ✅ 服务集成状态

## 📖 使用指南

### 🏗️ 构建知识图谱
1. 登录系统 (admin/admin123)
2. 上传文档 (PDF、Word、TXT)
3. 选择实体类型和关系类型
4. 点击"构建知识图谱"
5. 查看可视化结果

### 💬 智能问答
1. 进入"超级智能问答"页面
2. 选择知识库和知识图谱
3. 输入问题
4. 获得基于知识图谱和知识库的综合回答

### 📚 知识库管理
1. 通过Chatchat界面管理知识库
2. 上传文档到知识库
3. 配置向量化参数
4. 测试检索效果

## 🚀 部署选项

### 🏠 本地开发
- 使用快速启动脚本
- SQLite数据库
- 适合开发和测试

### 🐳 Docker部署
```bash
# 使用Docker Compose
docker-compose -f docker-compose.full.yml up -d
```

### ☁️ 云服务器
- 参考 `COMPLETE_DEPLOYMENT_GUIDE.md`
- 支持各种云平台
- 包含SSL配置

## 📚 文档资源

- **📖 完整部署指南**: `COMPLETE_DEPLOYMENT_GUIDE.md`
- **🧹 项目清理报告**: `PROJECT_CLEANUP_REPORT.md`
- **🚀 部署脚本**: `deploy_with_chatchat.sh`
- **🔍 状态检查**: `check_system_status.py`

## 🆘 故障排除

### 常见问题

#### 🔌 端口占用
```bash
# 检查端口占用
netstat -tulpn | grep :8000
netstat -tulpn | grep :7861

# 停止占用进程
kill -9 <PID>
```

#### 🗄️ 数据库连接失败
```bash
# 检查MySQL服务
sudo systemctl status mysql

# 检查配置
cat .env | grep DB_
```

#### 🤖 Chatchat启动失败
```bash
# 检查Python环境
which python
python --version

# 检查依赖
pip list | grep langchain
```

### 🔧 重置系统
```bash
# 清理安装
./deploy_with_chatchat.sh -c

# 重新安装
./deploy_with_chatchat.sh -m dev
```

## 🤝 贡献指南

欢迎提交Issue和Pull Request！

### 开发环境设置
1. Fork项目
2. 创建功能分支
3. 提交更改
4. 创建Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 🙏 致谢

- [LangChain-Chatchat](https://github.com/chatchat-space/Langchain-Chatchat) - 智能问答引擎
- [Django](https://www.djangoproject.com/) - Web框架
- [Neo4j](https://neo4j.com/) - 图数据库
- [vis.js](https://visjs.org/) - 图可视化

---

**🌟 如果这个项目对您有帮助，请给个Star支持一下！**

**📧 有问题？欢迎提Issue或联系我们！**
