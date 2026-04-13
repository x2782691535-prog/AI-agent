#!/bin/bash

# Django项目自动部署脚本
# 使用方法: ./deploy.sh [production|staging]

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查参数
ENVIRONMENT=${1:-production}
if [[ "$ENVIRONMENT" != "production" && "$ENVIRONMENT" != "staging" ]]; then
    log_error "环境参数错误。使用方法: ./deploy.sh [production|staging]"
    exit 1
fi

log_info "开始部署到 $ENVIRONMENT 环境..."

# 项目配置
PROJECT_NAME="DLR"
PROJECT_DIR="/var/www/dlr"
VENV_DIR="$PROJECT_DIR/venv"
BACKUP_DIR="/var/backups/dlr"

# 创建备份目录
sudo mkdir -p $BACKUP_DIR

# 1. 备份当前版本
log_info "备份当前版本..."
BACKUP_NAME="backup_$(date +%Y%m%d_%H%M%S)"
if [ -d "$PROJECT_DIR" ]; then
    sudo cp -r $PROJECT_DIR $BACKUP_DIR/$BACKUP_NAME
    log_info "备份完成: $BACKUP_DIR/$BACKUP_NAME"
fi

# 2. 更新代码
log_info "更新代码..."
cd $PROJECT_DIR
sudo git fetch origin
sudo git reset --hard origin/main

# 3. 激活虚拟环境
log_info "激活虚拟环境..."
source $VENV_DIR/bin/activate

# 4. 安装/更新依赖
log_info "安装依赖..."
pip install -r requirements.txt

# 5. 数据库迁移
log_info "执行数据库迁移..."
python manage.py migrate --settings=DLR.settings_production

# 6. 收集静态文件
log_info "收集静态文件..."
python manage.py collectstatic --noinput --settings=DLR.settings_production

# 7. 重启服务
log_info "重启服务..."
sudo supervisorctl restart dlr
sudo systemctl reload nginx

# 8. 健康检查
log_info "执行健康检查..."
sleep 5

# 检查应用是否正常运行
if curl -f http://localhost/health/ > /dev/null 2>&1; then
    log_info "✅ 部署成功！应用正常运行"
else
    log_error "❌ 部署失败！应用无法访问"
    
    # 回滚到备份版本
    log_warn "正在回滚到备份版本..."
    sudo rm -rf $PROJECT_DIR
    sudo cp -r $BACKUP_DIR/$BACKUP_NAME $PROJECT_DIR
    sudo supervisorctl restart dlr
    sudo systemctl reload nginx
    
    log_error "已回滚到备份版本"
    exit 1
fi

# 9. 清理旧备份（保留最近5个）
log_info "清理旧备份..."
cd $BACKUP_DIR
sudo ls -t | tail -n +6 | xargs -r sudo rm -rf

log_info "🎉 部署完成！"
log_info "访问地址: http://your-domain.com"
