# 🚀 DLR + LangChain-Chatchat 完整部署指南

## 📋 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                    DLR 知识图谱系统                          │
├─────────────────────────────────────────────────────────────┤
│  📊 知识图谱构建  │  🎨 可视化  │  👥 用户管理  │  📄 文档处理  │
└─────────────────────────────────────────────────────────────┘
                              ↕️ API调用
┌─────────────────────────────────────────────────────────────┐
│                 LangChain-Chatchat 系统                     │
├─────────────────────────────────────────────────────────────┤
│  💬 智能问答  │  📚 知识库  │  🤖 大模型  │  🔍 向量检索     │
└─────────────────────────────────────────────────────────────┘
```

## 🎯 功能说明

### DLR系统功能
- ✅ **知识图谱构建**: 文档解析、实体识别、关系抽取
- ✅ **图谱可视化**: 多布局交互式可视化
- ✅ **用户管理**: 认证、权限、多用户支持
- ✅ **文档管理**: PDF、Word、TXT文件处理

### Chatchat系统功能
- 🤖 **智能问答**: 基于知识库的问答
- 📚 **知识库管理**: 文档向量化存储
- 🔍 **语义检索**: 高精度文档检索
- 💬 **对话记忆**: 上下文理解

### 集成功能
- 🌟 **超级智能问答**: 结合知识图谱和知识库的综合问答
- 🔗 **数据互通**: 知识图谱和知识库数据共享
- 📊 **统一管理**: 一个界面管理所有功能

## 🚀 快速启动（推荐）

### 一键启动脚本

#### Windows用户
```bash
# 双击运行或在命令行执行
quick_start.bat
```

#### Linux/Mac用户
```bash
# 方式1: Python脚本
python quick_start.py

# 方式2: Shell脚本
chmod +x deploy_with_chatchat.sh
./deploy_with_chatchat.sh -m dev
```

#### 快速启动功能
- ✅ **自动检查环境**: Python、Git、端口占用
- ✅ **自动安装依赖**: DLR + Chatchat所有依赖
- ✅ **自动配置环境**: 创建.env文件和数据库
- ✅ **自动启动服务**: 同时启动DLR和Chatchat
- ✅ **一键完成**: 5分钟内完成所有配置

## 🛠️ 详细部署方案

### 方案一：本地开发环境（推荐新手）

#### 1. 环境准备
```bash
# Python 3.8-3.11
# MySQL 8.0+
# Neo4j 5.0+
# Git
```

#### 2. 克隆和设置DLR
```bash
# 克隆项目
git clone <your-dlr-repo>
cd DLR

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows

# 安装依赖
pip install -r requirements.txt
```

#### 3. 安装LangChain-Chatchat
```bash
# 克隆Chatchat项目
cd ..
git clone https://github.com/chatchat-space/Langchain-Chatchat.git
cd Langchain-Chatchat

# 安装Chatchat
pip install -e .

# 初始化配置
python copy_config_example.py
```

#### 4. 配置数据库
```bash
# 配置MySQL
mysql -u root -p
CREATE DATABASE dlr_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'dlr_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON dlr_db.* TO 'dlr_user'@'localhost';

# 配置Neo4j
# 启动Neo4j服务，设置密码
```

#### 5. 配置环境变量
```bash
# DLR/.env
DEBUG=True
SECRET_KEY=your-secret-key
DB_NAME=dlr_db
DB_USER=dlr_user
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=3306
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_neo4j_password
CHATCHAT_API_BASE_URL=http://127.0.0.1:7861
```

#### 6. 启动服务
```bash
# 终端1: 启动Chatchat
cd Langchain-Chatchat
python startup.py -a

# 终端2: 启动DLR
cd DLR
python manage.py migrate
python manage.py runserver 8000
```

#### 7. 访问系统
- **DLR主界面**: http://localhost:8000
- **Chatchat界面**: http://localhost:8501
- **API文档**: http://localhost:7861/docs

### 方案二：Docker容器部署（推荐生产）

#### 1. 创建Docker Compose配置
```yaml
# docker-compose.full.yml
version: '3.8'

services:
  mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: rootpassword
      MYSQL_DATABASE: dlr_db
      MYSQL_USER: dlr_user
      MYSQL_PASSWORD: dlrpassword
    volumes:
      - mysql_data:/var/lib/mysql
    ports:
      - "3306:3306"

  neo4j:
    image: neo4j:5.0
    environment:
      NEO4J_AUTH: neo4j/neo4jpassword
      NEO4J_PLUGINS: '["apoc"]'
    volumes:
      - neo4j_data:/data
    ports:
      - "7474:7474"
      - "7687:7687"

  chatchat:
    build:
      context: ./Langchain-Chatchat
      dockerfile: Dockerfile
    environment:
      - CHATCHAT_ROOT=/app/chatchat_data
    volumes:
      - chatchat_data:/app/chatchat_data
      - ./models:/app/models
    ports:
      - "7861:7861"
      - "8501:8501"
    depends_on:
      - mysql

  dlr:
    build:
      context: .
      dockerfile: Dockerfile
    environment:
      - DEBUG=False
      - DB_HOST=mysql
      - NEO4J_URI=bolt://neo4j:7687
      - CHATCHAT_API_BASE_URL=http://chatchat:7861
    volumes:
      - ./media:/app/media
    ports:
      - "8000:8000"
    depends_on:
      - mysql
      - neo4j
      - chatchat

  nginx:
    image: nginx:alpine
    volumes:
      - ./nginx.full.conf:/etc/nginx/nginx.conf
    ports:
      - "80:80"
    depends_on:
      - dlr
      - chatchat

volumes:
  mysql_data:
  neo4j_data:
  chatchat_data:
```

#### 2. 创建Chatchat Dockerfile
```dockerfile
# Langchain-Chatchat/Dockerfile
FROM python:3.10-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# 复制项目文件
COPY . .

# 安装Python依赖
RUN pip install -e . -i https://pypi.tuna.tsinghua.edu.cn/simple

# 初始化配置
RUN python copy_config_example.py

# 暴露端口
EXPOSE 7861 8501

# 启动命令
CMD ["python", "startup.py", "-a", "--host", "0.0.0.0"]
```

#### 3. 创建Nginx配置
```nginx
# nginx.full.conf
events {
    worker_connections 1024;
}

http {
    upstream dlr_backend {
        server dlr:8000;
    }
    
    upstream chatchat_api {
        server chatchat:7861;
    }
    
    upstream chatchat_ui {
        server chatchat:8501;
    }

    server {
        listen 80;
        server_name localhost;

        # DLR主应用
        location / {
            proxy_pass http://dlr_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }

        # Chatchat API
        location /api/ {
            proxy_pass http://chatchat_api/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }

        # Chatchat UI
        location /chatchat/ {
            proxy_pass http://chatchat_ui/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }
    }
}
```

#### 4. 启动完整系统
```bash
# 构建和启动所有服务
docker-compose -f docker-compose.full.yml up -d

# 查看服务状态
docker-compose -f docker-compose.full.yml ps

# 查看日志
docker-compose -f docker-compose.full.yml logs -f
```

### 方案三：云服务器部署

#### 1. 服务器要求
- **CPU**: 4核心以上
- **内存**: 16GB以上
- **存储**: 100GB以上
- **系统**: Ubuntu 20.04+

#### 2. 安装基础环境
```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 安装Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 安装Git
sudo apt install git -y
```

#### 3. 部署项目
```bash
# 克隆项目
git clone <your-dlr-repo>
cd DLR

# 克隆Chatchat
git clone https://github.com/chatchat-space/Langchain-Chatchat.git

# 配置环境变量
cp .env.example .env
# 编辑.env文件，设置生产环境配置

# 启动服务
docker-compose -f docker-compose.full.yml up -d
```

#### 4. 配置域名和SSL
```bash
# 安装Certbot
sudo apt install certbot python3-certbot-nginx -y

# 获取SSL证书
sudo certbot --nginx -d yourdomain.com

# 设置自动续期
sudo crontab -e
# 添加: 0 12 * * * /usr/bin/certbot renew --quiet
```

## 🔧 配置说明

### DLR配置文件
```python
# DLR/settings_production.py
DEBUG = False
ALLOWED_HOSTS = ['yourdomain.com', 'localhost']

# Chatchat集成配置
CHATCHAT_API_BASE_URL = "http://chatchat:7861"  # Docker内部
# CHATCHAT_API_BASE_URL = "http://localhost:7861"  # 本地开发

# 知识库配置
KNOWLEDGE_BASE_CONFIG = {
    'default_kb': 'samples',
    'chunk_size': 500,
    'chunk_overlap': 50,
    'vector_store_type': 'faiss',
    'embed_model': 'bge-large-zh-v1.5'
}
```

### Chatchat配置文件
```python
# Langchain-Chatchat/configs/model_config.py
# 模型配置
LLM_MODELS = ["deepseek-r1", "qwen-plus", "glm-4"]
EMBEDDING_MODEL = "bge-large-zh-v1.5"

# API配置
API_SERVER = {
    "host": "0.0.0.0",
    "port": 7861,
}

# 知识库配置
KB_ROOT_PATH = "/app/chatchat_data/knowledge_base"
DB_ROOT_PATH = "/app/chatchat_data/knowledge_base/info.db"
```

## 🎯 使用指南

### 1. 创建知识库
```python
# 在DLR界面中
1. 上传文档到DLR系统
2. 构建知识图谱
3. 同步到Chatchat知识库
4. 开始智能问答
```

### 2. 超级智能问答
```python
# 结合知识图谱和知识库的问答
POST /api/super_chat/
{
    "question": "什么是机器学习？",
    "kb_name": "ai_textbook",
    "kg_id": 1,
    "model": "deepseek-r1"
}
```

### 3. API接口
- **DLR API**: http://localhost:8000/api/
- **Chatchat API**: http://localhost:7861/docs
- **健康检查**: http://localhost:8000/health/

## 🚨 故障排除

### 常见问题

#### 1. Chatchat连接失败
```bash
# 检查Chatchat服务状态
curl http://localhost:7861/health

# 检查DLR配置
python manage.py shell
>>> from django.conf import settings
>>> print(settings.CHATCHAT_API_BASE_URL)
```

#### 2. 知识库同步失败
```bash
# 检查知识库列表
curl http://localhost:7861/knowledge_base/list_knowledge_bases

# 重新同步
python manage.py shell
>>> from lcc.kb_service import KnowledgeBaseService
>>> kb = KnowledgeBaseService()
>>> kb.list_knowledge_bases()
```

#### 3. 模型加载失败
```bash
# 检查模型配置
curl http://localhost:7861/llm_model/list_running_models

# 重启Chatchat
docker-compose restart chatchat
```

## 📊 性能优化

### 1. 硬件建议
- **开发环境**: 8GB内存，4核CPU
- **生产环境**: 32GB内存，8核CPU，GPU可选

### 2. 配置优化
```python
# 增加超时时间
CHATCHAT_TIMEOUT = 300

# 优化向量检索
VECTOR_SEARCH_TOP_K = 5
SCORE_THRESHOLD = 0.7

# 缓存配置
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
    }
}
```

## 🎉 部署完成

部署完成后，您将拥有：

✅ **完整的知识图谱系统**
✅ **智能问答功能**
✅ **知识库管理**
✅ **超级智能对话**
✅ **可视化界面**
✅ **用户管理系统**
✅ **API接口**
✅ **生产环境配置**

**🌟 现在您可以享受完整的AI知识管理体验了！**
