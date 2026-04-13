#!/bin/bash

# DLR + LangChain-Chatchat 自动化部署脚本
# 支持本地开发和生产环境部署

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查命令是否存在
check_command() {
    if ! command -v $1 &> /dev/null; then
        log_error "$1 未安装，请先安装 $1"
        exit 1
    fi
}

# 检查端口是否被占用
check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null ; then
        log_warning "端口 $1 已被占用"
        return 1
    fi
    return 0
}

# 显示帮助信息
show_help() {
    echo "DLR + LangChain-Chatchat 部署脚本"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  -m, --mode MODE     部署模式: dev(开发) 或 prod(生产) [默认: dev]"
    echo "  -d, --docker        使用Docker部署"
    echo "  -c, --clean         清理现有安装"
    echo "  -h, --help          显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 -m dev           # 开发环境部署"
    echo "  $0 -m prod -d       # 生产环境Docker部署"
    echo "  $0 -c               # 清理安装"
}

# 清理安装
clean_install() {
    log_info "清理现有安装..."
    
    # 停止Docker服务
    if [ -f "docker-compose.yml" ]; then
        docker-compose down -v 2>/dev/null || true
    fi
    
    if [ -f "docker-compose.full.yml" ]; then
        docker-compose -f docker-compose.full.yml down -v 2>/dev/null || true
    fi
    
    # 清理Python虚拟环境
    if [ -d "venv" ]; then
        rm -rf venv
        log_success "已清理Python虚拟环境"
    fi
    
    # 清理Chatchat目录
    if [ -d "Langchain-Chatchat" ]; then
        rm -rf Langchain-Chatchat
        log_success "已清理Chatchat目录"
    fi
    
    log_success "清理完成"
}

# 检查系统环境
check_environment() {
    log_info "检查系统环境..."
    
    # 检查Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python3 未安装"
        exit 1
    fi
    
    python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    log_info "Python版本: $python_version"
    
    if [[ "$python_version" < "3.8" ]]; then
        log_error "Python版本需要 >= 3.8"
        exit 1
    fi
    
    # 检查Git
    check_command git
    
    # 检查pip
    check_command pip3
    
    log_success "系统环境检查通过"
}

# 安装DLR依赖
install_dlr() {
    log_info "安装DLR依赖..."
    
    # 创建虚拟环境
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        log_success "创建Python虚拟环境"
    fi
    
    # 激活虚拟环境
    source venv/bin/activate
    
    # 升级pip
    pip install --upgrade pip
    
    # 安装依赖
    pip install -r requirements.txt
    
    log_success "DLR依赖安装完成"
}

# 安装Chatchat
install_chatchat() {
    log_info "安装LangChain-Chatchat..."
    
    # 克隆Chatchat项目
    if [ ! -d "Langchain-Chatchat" ]; then
        git clone https://github.com/chatchat-space/Langchain-Chatchat.git
        log_success "克隆Chatchat项目"
    else
        log_info "Chatchat项目已存在，跳过克隆"
    fi
    
    cd Langchain-Chatchat
    
    # 激活虚拟环境
    source ../venv/bin/activate
    
    # 安装Chatchat
    pip install -e .
    
    # 初始化配置
    if [ ! -f "configs/model_config.py" ]; then
        python copy_config_example.py
        log_success "初始化Chatchat配置"
    fi
    
    cd ..
    
    log_success "Chatchat安装完成"
}

# 配置环境变量
setup_environment() {
    log_info "配置环境变量..."
    
    if [ ! -f ".env" ]; then
        cp .env.example .env
        log_success "创建环境变量文件"
        
        log_warning "请编辑 .env 文件配置数据库和其他设置"
        log_info "主要配置项："
        log_info "  - DB_NAME, DB_USER, DB_PASSWORD"
        log_info "  - NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD"
        log_info "  - SECRET_KEY"
    else
        log_info "环境变量文件已存在"
    fi
}

# 初始化数据库
init_database() {
    log_info "初始化数据库..."
    
    source venv/bin/activate
    
    # Django数据库迁移
    python manage.py makemigrations
    python manage.py migrate
    
    # 创建超级用户（如果不存在）
    echo "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.filter(username='admin').exists() or User.objects.create_superuser('admin', 'admin@example.com', 'admin123')" | python manage.py shell
    
    log_success "数据库初始化完成"
    log_info "管理员账号: admin / admin123"
}

# 开发环境部署
deploy_dev() {
    log_info "开始开发环境部署..."
    
    check_environment
    install_dlr
    install_chatchat
    setup_environment
    init_database
    
    log_success "开发环境部署完成！"
    log_info ""
    log_info "启动服务："
    log_info "1. 启动Chatchat:"
    log_info "   cd Langchain-Chatchat && source ../venv/bin/activate && python startup.py -a"
    log_info ""
    log_info "2. 启动DLR (新终端):"
    log_info "   source venv/bin/activate && python manage.py runserver 8000"
    log_info ""
    log_info "访问地址："
    log_info "  - DLR主界面: http://localhost:8000"
    log_info "  - Chatchat界面: http://localhost:8501"
    log_info "  - API文档: http://localhost:7861/docs"
}

# Docker部署
deploy_docker() {
    log_info "开始Docker部署..."
    
    # 检查Docker
    check_command docker
    check_command docker-compose
    
    # 创建完整的docker-compose文件
    create_docker_compose
    
    # 构建和启动服务
    docker-compose -f docker-compose.full.yml up -d --build
    
    log_success "Docker部署完成！"
    log_info "访问地址: http://localhost"
    log_info "查看状态: docker-compose -f docker-compose.full.yml ps"
    log_info "查看日志: docker-compose -f docker-compose.full.yml logs -f"
}

# 创建Docker Compose文件
create_docker_compose() {
    log_info "创建Docker Compose配置..."
    
    cat > docker-compose.full.yml << 'EOF'
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
    restart: unless-stopped

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
    restart: unless-stopped

  dlr:
    build:
      context: .
      dockerfile: Dockerfile
    environment:
      - DEBUG=False
      - DB_HOST=mysql
      - DB_NAME=dlr_db
      - DB_USER=dlr_user
      - DB_PASSWORD=dlrpassword
      - NEO4J_URI=bolt://neo4j:7687
      - NEO4J_USER=neo4j
      - NEO4J_PASSWORD=neo4jpassword
      - CHATCHAT_API_BASE_URL=http://chatchat:7861
    volumes:
      - ./media:/app/media
    ports:
      - "8000:8000"
    depends_on:
      - mysql
      - neo4j
    restart: unless-stopped

volumes:
  mysql_data:
  neo4j_data:
EOF

    log_success "Docker Compose配置创建完成"
}

# 启动服务
start_services() {
    log_info "启动服务..."
    
    # 检查端口
    if ! check_port 7861; then
        log_error "Chatchat端口7861被占用，请先停止相关服务"
        exit 1
    fi
    
    if ! check_port 8000; then
        log_error "DLR端口8000被占用，请先停止相关服务"
        exit 1
    fi
    
    # 启动Chatchat (后台)
    cd Langchain-Chatchat
    source ../venv/bin/activate
    nohup python startup.py -a > ../chatchat.log 2>&1 &
    CHATCHAT_PID=$!
    echo $CHATCHAT_PID > ../chatchat.pid
    cd ..
    
    log_success "Chatchat已启动 (PID: $CHATCHAT_PID)"
    
    # 等待Chatchat启动
    log_info "等待Chatchat启动..."
    sleep 10
    
    # 启动DLR
    source venv/bin/activate
    log_info "启动DLR服务..."
    python manage.py runserver 8000
}

# 停止服务
stop_services() {
    log_info "停止服务..."
    
    # 停止DLR
    pkill -f "manage.py runserver" || true
    
    # 停止Chatchat
    if [ -f "chatchat.pid" ]; then
        kill $(cat chatchat.pid) || true
        rm chatchat.pid
    fi
    
    log_success "服务已停止"
}

# 主函数
main() {
    # 默认参数
    MODE="dev"
    USE_DOCKER=false
    CLEAN=false
    
    # 解析参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            -m|--mode)
                MODE="$2"
                shift 2
                ;;
            -d|--docker)
                USE_DOCKER=true
                shift
                ;;
            -c|--clean)
                CLEAN=true
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                log_error "未知参数: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # 显示配置
    log_info "部署配置："
    log_info "  模式: $MODE"
    log_info "  Docker: $USE_DOCKER"
    log_info "  清理: $CLEAN"
    log_info ""
    
    # 执行清理
    if [ "$CLEAN" = true ]; then
        clean_install
        exit 0
    fi
    
    # 执行部署
    if [ "$USE_DOCKER" = true ]; then
        deploy_docker
    elif [ "$MODE" = "dev" ]; then
        deploy_dev
    elif [ "$MODE" = "prod" ]; then
        log_error "生产环境部署请使用Docker模式: $0 -m prod -d"
        exit 1
    else
        log_error "无效的部署模式: $MODE"
        exit 1
    fi
}

# 运行主函数
main "$@"
